import sctour as sct
import scanpy as sc
import numpy as np
import pandas as pd
import json


def TrainScTourModel(GEXfile, exclusion_json_path, model_path_basedir, model_name, embedding_out_file, ptime_out_file, random_state = 0):
    print('Running scTour to train model')

    #read gene expression matrix and exclusion list
    adataObj = sc.read_10x_h5(GEXfile)

    #ensure expression matrix is integers
    adataObj.X = round(adataObj.X).astype(np.float32)

    if exclusion_json_path != None:
        with open(exclusion_json_path) as f:
            exclusionList = json.load(f)

        #apply exclusion list
        toKeep = list(set(adataObj.var_names) - set(exclusionList))
        adataObj = adataObj[:, toKeep]

    #basic preprocessing to population metadata fields that scTour expects
    sc.pp.calculate_qc_metrics(adataObj, percent_top=None, log1p=False, inplace=True)
    sc.pp.filter_genes(adataObj, min_cells=20)
    sc.pp.highly_variable_genes(adataObj, flavor='seurat_v3', n_top_genes=2000, subset=True, inplace=False)

    #train model
    tnode = sct.train.Trainer(adataObj, random_state = random_state)
    tnode.train()

    #apply model to get pseudotime (ptime)
    adataObj.obs['ptime'] = tnode.get_time()
    mix_zs, zs, pred_zs = tnode.get_latentsp(alpha_z=0.2, alpha_predz=0.8)
    #obtain latent space for dimensional reduction in R/Seurat
    adataObj.obsm['X_TNODE'] = mix_zs

    #save model (note, it is necessary to save the model AFTER tnode.get_time())
    tnode.save_model(model_path_basedir, model_name)

    #write embeddings
    np.savetxt(embedding_out_file, adataObj.obsm['X_TNODE'] , delimiter=",")

    #write pseudotime to be appended to the seurat object
    df = pd.DataFrame(adataObj.obs['ptime'])
    df.to_csv(ptime_out_file)

    return adataObj
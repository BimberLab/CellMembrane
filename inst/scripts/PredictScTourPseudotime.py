import sctour as sct
import scanpy as sc
import numpy as np
import pandas as pd
import torch
import itertools

def PredictPseudotime(GEXfile, model_file, ptime_out_file, embedding_out_file):
    #read count data and variable genes
    adataObj = sc.read_10x_h5(GEXfile)

    checkpoint = torch.load(model_file, map_location=torch.device('cpu'))
    model_adata = checkpoint['adata']

    print('REMOVE THIS')
    print(model_adata)
    print(model_adata.var_names)

    genes_in_model = model_adata.var_names
    genes_in_model = list(itertools.chain.from_iterable(genes_in_model.values.tolist()))
    
    #basic preprocessing
    adataObj.X = round(adataObj.X).astype(np.float32)
    sc.pp.calculate_qc_metrics(adataObj, percent_top=None, log1p=False, inplace=True)
    sc.pp.filter_genes(adataObj, min_cells=20)
    sc.pp.highly_variable_genes(adataObj, flavor='seurat_v3', n_top_genes=2000, subset=True, inplace=False)
    
    #subset to genes found in the pretrained model.
    adataObj = adataObj[:, genes_in_model]
    #initalize a trainer and pull a previously saved model from model_file
    tnode = sct.predict.load_model(model_file)
    pred_t = sct.predict.predict_time(adata = adataObj, model = tnode)
    adataObj.obs['ptime'] = pred_t
    mix_zs, zs, pred_zs  = sct.predict.predict_latentsp(adata = adataObj, model = tnode)
    adataObj.obsm['X_TNODE'] = mix_zs
    np.savetxt(embedding_out_file, adataObj.obsm['X_TNODE'] , delimiter=",")

    df = pd.DataFrame(adataObj.obs['ptime'])
    df.to_csv(ptime_out_file)

    return adataObj

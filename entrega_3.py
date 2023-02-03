

from google.colab import driv
drive.mount('/content/drive')

import pandas as pd

data= pd.read_csv('metadata.csv', sep=';',engine='python')

data.head()

data.isna().sum()

"""Se procede a dropear las primeras 3 columnas que considero no son necesarios"""

data.drop(['episode_title', 'cast_first_name', 'credits_first_name'], axis=1, inplace=True)

"""Se cambia el formato de la fecha para que sea mas sencillo operar con la  variable que indica hasta cuando va a estar disponible en la plataforma el contenido para visualizar"""

from datetime import datetime

# Commented out IPython magic to ensure Python compatibility.
# %%time
# data["end_vod_date"] = pd.to_datetime(data.end_vod_date)

data["start_vod_date"] = pd.to_datetime(data.start_vod_date)

data['end_vod_date'] = data['end_vod_date'].apply(lambda x: x.replace(tzinfo=None).date())

data['start_vod_date'] = data['start_vod_date'].apply(lambda x: x.replace(tzinfo=None).date())

data.shape

"""La cantidad de perfiles de la plataforma Flow es 33144

"""

data.asset_id.nunique()

data_train= pd.read_csv('train.csv')

data_train.head()

data_train.shape

"""El dataset 'data_train' contiene 3657801 filas, y 7 columnas


"""

# Commented out IPython magic to ensure Python compatibility.
# %%time
# data_train['tunein'] = pd.to_datetime(data_train.tunein)

data_train['tunein'] = data_train['tunein'].apply(lambda x: x.replace(tzinfo=None).date())

# Commented out IPython magic to ensure Python compatibility.
# %%time
# data_train['tuneout'] = pd.to_datetime(data_train.tuneout)

data_train['tuneout'] = data_train['tuneout'].apply(lambda x: x.replace(tzinfo=None).date())

data_train.head()

df = pd.merge(data[['asset_id','content_id','title','create_date','modify_date','start_vod_date','end_vod_date']],
              data_train[['account_id',	'device_type','asset_id','tunein','tuneout','resume']], 
              how = 'inner', 
              on = 'asset_id')

df.rename({'resume':'rating'},axis=1, inplace=True)

"""Cambio de nombre de la columna que tomare como rating, considerando 0= no vió el contenido( no retoma la visualización),
             1= vió el contenido (retoma la visualización)

"""

df.head()

df.shape

df.info()

df.isna().sum()

df.content_id.nunique()

"""Se eliminan registros duplicados"""

df = df.drop_duplicates()

"""Intervalo de fecha  mínima y máxima de reviews"""

df.tunein.min()

df.tunein.max()

df.tuneout.min()

df.tuneout.max()

"""Se incluye el filtro de contenido que no esta disponible en la plataforma en el set test"""

train = df[df.tunein <= datetime(2021, 3, 1).date()]

test = df[(df.tunein > datetime(2021, 3, 1).date())]

train.head()

train.shape

test.shape

"""Se Arma la matriz de interacciones con las columnas seleccionadas


"""

interactions  =  train[[ 'account_id' , 'content_id' , 'rating' ]].copy()
interactions_matrix = pd .pivot_table ( interactions , index = 'account_id' , columns ='content_id' , values = 'rating' )

"""Se reemplazan los Nan con 0



"""

interactions_matrix

interactions_matrix = interactions_matrix.fillna(0)

interactions_matrix.shape

interactions_matrix.head()

from scipy.sparse import csr_matrix

interactions_matrix_csr = csr_matrix(interactions_matrix.values)

interactions_matrix_csr

user_ids  =  list ( interactions_matrix. index )
user_dict  = {}
contador  =  0
for  i  in  user_ids :
        user_dict [ i ] =  contador
        contador  +=  1

user_dict

item_id  =  list (interactions_matrix.columns )
item_dict  = {}
contador  =  0 
for  i  in  item_id :
    item_dict [ i ] =  contador
    contador  +=  1

"""
Se entrena el modelo



"""

pip install lightfm

from lightfm import LightFM

model = LightFM(random_state=0,
                loss='warp',
                learning_rate=0.03,
                no_components=100)

model = model.fit(interactions_matrix_csr,
                  epochs=100,
                  num_threads=16, verbose=False)

train.groupby("content_id", as_index=False).agg({'account_id':"nunique"})

popularity_df = train.groupby('content_id', as_index=False).agg({"account_id":"nunique"}).sort_values(by="account_id", ascending=False)

popularity_df.columns=["content_id", "popularity"]
popularity_df.head(10)

popular_content = popularity_df.content_id.values[:10]

popular_content

"""Cantidad de perfiles que estan en test y no estan en train. Cold Star."""

test[~test.account_id.isin(train.account_id.unique())].account_id.nunique()

"""Se define donde van a estar guardando las recomendaciones

"""

from tqdm import tqdm


recomms_dict = {
    'account_id': [],
    'recomms': []
}

import numpy as np

#obtenemos cantidad de usuarios y cantidad de items
user_ids,item_ids=  interactions_matrix.shape
item_ids = np .arange (item_ids )

#por cada usuario del dataset de test, generamos recomendaciones
for user in tqdm(test.content_id.unique()):
    
    # si el usuario se encuentra en la matriz de interacciones (interactions_matrix.index)
    if user in list(interactions_matrix.index):
     
      # Si el usuario esta en train, no es cold start. Usamos el modelo para recomendar
      user_x = user_dict[user] #buscamos el indice del usuario en la matriz (transformamos id a indice)

      #COMPLETAR: Generar las predicciones para el usuario x
      preds = model.predict(user_ids=user_x, item_ids = item_ids)

      #COMPLETAR: Basándose en el ejemplo anterior, ordenar las predicciones de menor a mayor y quedarse con 50.
      scores = pd.Series(preds)
      scores.index = interactions_matrix.columns
      scores = list(pd.Series(scores.sort_values(ascending=False).index))[:50]

      # listado de contenidos vistos anteriormente por el usuario (en el set de train)
      watched_contents = train[train.account_id == user].content_id.unique()

      #COMPLETAR: Filtrar contenidos ya vistos y quedarse con los primeros 10
      recomms = [x for x in scores if x not in watched_contents][:20]

      # Guardamos las recomendaciones en el diccionario
      recomms_dict['account_id'].append(user)
      recomms_dict['recomms'].append(scores)
    
    # En este else trataremos a los usuarios que no están en la matriz (cold start)
    else:
      recomms_dict['account_id'].append(user)
      # Les recomendamos contenido popular
      recomms_dict['recomms'].append(popular_content)

recomms_df = pd.DataFrame(recomms_dict)

recomms_df

ideal_recomms = test.sort_values(by=["account_id", "rating"], ascending=False)\
                  .groupby(["account_id"], as_index=False)\
                  .agg({"content_id": "unique"})\
                  .head()
ideal_recomms.head()

"""Se define MAP

"""

df_map = ideal_recomms.merge(recomms_df, how="left", left_on="account_id", right_on="account_id")[["account_id", "content_id","recomms"]]
df_map.columns = ["account_id", "ideal", "recomms"]
df_map.head()

aps = [] # lista vacía para ir almacenando la AP de cada recomendación
for pred, label in df_map[["ideal", "recomms"]].values:
  n = len(pred) # cantidad de elementos recomendados
  arange = np.arange(n, dtype=np.int32) + 1. # indexamos en base 1 
  rel_k = np.in1d(pred[:n], label) # lista de booleanos que indican la relevancia de cada ítem
  tp = np.ones(rel_k.sum(), dtype=np.int32).cumsum() # lista con el contador de verdaderos positivos
  denom = arange[rel_k] # posiciones donde se encuentran los ítems relantes
  ap = (tp / denom).sum() / len(label) # average precision
  aps.append(ap)

MAP = np.mean(aps)
print(f'mean average precision = {round(MAP, 5)}')

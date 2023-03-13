import configparser
import pyodbc
import pandas as pd
import http.client
import json

# Load configuration from config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Get server information from environment variables
server_driver = config['SQL_SERVER']['driver']
server_name = config['SQL_SERVER']['name']
database_name = config['SQL_DATABASE']['name']
username = config['SQL_AUTHENTICATION']['username']
password = config['SQL_AUTHENTICATION']['password']

# Define the connection string to your SQL Server instance
conn_str = f"DRIVER={server_driver};SERVER={server_name};DATABASE={database_name};UID={username};PWD={password}"

# Create a connection object and cursor
cnxn = pyodbc.connect(conn_str)
cursor = cnxn.cursor()

df_sql = pd.read_sql_query("select * from PROD_ECOM_COR_001", cnxn)

# Print the results
print(df_sql.head(2))
print(df_sql.columns)
print(df_sql.head(2)['ATRIBUTO_1'])

# Close the cursor and connection
cursor.close()
cnxn.close()

# Parameters to connect to VTEX API
conn = http.client.HTTPSConnection("dalcosta.vtexcommercestable.com.br")
vtex_api_appkey = config['VTEX_AUTHENTICATION']['vtex_api_appkey']
vtex_api_apptoken = config['VTEX_AUTHENTICATION']['vtex_api_apptoken']

headers = {
    'Accept': "application/json",
    'Content-Type': "application/json",
    'X-VTEX-API-AppKey': vtex_api_appkey,
    'X-VTEX-API-AppToken': vtex_api_apptoken
    }

# Get the full list of SKU ID from VTEX (WARNING CHANGE THE PAGESIZE)
conn.request("get", "/api/catalog_system/pvt/sku/stockkeepingunitids?page=1&pagesize=600", headers=headers)
res = conn.getresponse()
data = res.read()
decoded_data = data.decode("utf-8")
skuid_list = json.loads(decoded_data)

# print(skuid_list) # print skuid_list just for test
sku_data_list = []
# Get all information of each SKU ID
for sku in skuid_list:
    conn.request("get", "/api/catalog_system/pvt/sku/stockkeepingunitbyid/" + str(sku), headers=headers)
    res = conn.getresponse()
    skuid_data = res.read()
    decoded_skuid_data = skuid_data.decode("utf-8")
    skuid_data_converted = json.loads(decoded_skuid_data)
    sku_data_list.append(skuid_data_converted)
    
# Convert to Dataframe and normalize
df_vtex = pd.json_normalize(sku_data_list)
print(df_vtex.columns)

# First validation
df_product_id = df_vtex[['Id', 'ProductId', 'ProductRefId', 'AlternateIds.RefId']]
df_product_id['AlternateIds.RefId'] = df_product_id['AlternateIds.RefId'].str[:9]
df_product_id = df_product_id.astype(str)
# print(df_product_id)
# print(df_product_id.dtypes)

not_equals_product_id = df_product_id[(df_product_id['ProductId'] != df_product_id['ProductRefId']) | (df_product_id['ProductId'] != df_product_id['AlternateIds.RefId']) | (df_product_id['ProductRefId'] != df_product_id['AlternateIds.RefId'])]
if not_equals_product_id.empty:
    print('Todos os produtos estão com as informações ProductId, ProductRefId e AlternateIds.RefId corretas')
else: 
    print('Os seguintes SkuIDs/Referências estão com divergência no cadastro de produto nos campos ProductId, ProductRefId e AlternateIds.RefId:')
    print(not_equals_product_id)


# VERIFICAR SE NA LISTA DE PRODUTOS COM ERRO APARECE O ID DO SKU TB
# O REQUEST DE ITEM POR ITEM ESTÁ DEMORANDO MUITO, TALVEZ NÃO TENHA O QUE FAZER
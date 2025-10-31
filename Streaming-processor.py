nouveau streaming_processor :
import os
import psycopg2
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode, size
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType, IntegerType,
    ArrayType, DoubleType, BooleanType
)
 
# === 1. Configurations ===
# Les packages JAR sont fournis par la commande spark-submit --packages
# KAFKA_VERSION = "3.5.0"
# POSTGRES_VERSION = "42.7.3"
# KAFKA_PACKAGES = f"org.apache.spark:spark-sql-kafka-0-10_2.12:{KAFKA_VERSION}"
# POSTGRES_PACKAGES = f"org.postgresql:postgresql:{POSTGRES_VERSION}"
 
PG_URL = "jdbc:postgresql://postgres:5432/mydb"
PG_TABLE = "airports"
PG_PROPERTIES = {
    "user": "admin",
    "password": "admin",
    "driver": "org.postgresql.Driver"
}
KAFKA_BOOTSTRAP_SERVERS = "kafka:9093" # Assurez-vous que c'est le bon port (9092 ou 9093)
KAFKA_TOPIC = "airports"
 
 
# === 2. Création / Réinitialisation de la table PostgreSQL ===
def initialize_postgres_table():
    print("Initialisation de la base PostgreSQL...")
   
    # Nettoie les anciens checkpoints Spark qui auraient pu planter
    print("Nettoyage des anciens checkpoints Spark (/tmp/temporary-*)...")
    os.system("rm -rf /tmp/temporary-*")
   
    try:
        conn = psycopg2.connect(
            host="postgres",
            port=5432,
            dbname="mydb",
            user=PG_PROPERTIES["user"],
            password=PG_PROPERTIES["password"]
        )
        cur = conn.cursor()
 
        cur.execute(f"DROP TABLE IF EXISTS {PG_TABLE};")
        print(f"Ancienne table '{PG_TABLE}' supprimée (si existait).")
 
        cur.execute(f"""
            CREATE TABLE {PG_TABLE} (
                airport_id TEXT,
                name TEXT,
                icao TEXT,
                iata TEXT,
                country TEXT,
                longitude DOUBLE PRECISION,
                latitude DOUBLE PRECISION,
                airport_type INTEGER,
                elevation_meters FLOAT,
                mag_declination FLOAT,
                ppr BOOLEAN,
                is_private BOOLEAN,
                skydive_activity BOOLEAN,
                winch_only BOOLEAN,
                runway_count INTEGER,
                created_at TEXT,
                updated_at TEXT,
                created_by TEXT,
                updated_by TEXT,
                geoid_height FLOAT,
                hae FLOAT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print(f"Table '{PG_TABLE}' recréée avec succès.\n")
    except Exception as e:
        print(f"ERREUR lors de l'initialisation de Postgres: {e}")
        print("Veuillez vérifier que le service 'postgres' est accessible et que les identifiants sont corrects.")
        pass # On continue quand même, Spark plantera plus tard si c'est grave
 
# On exécute la réinitialisation au démarrage
initialize_postgres_table()
 
 
# === 3. Schémas ===
GEOMETRY_SCHEMA = StructType([
    StructField("type", StringType(), True),
    StructField("coordinates", ArrayType(DoubleType()), True)
])
 
ELEVATION_SCHEMA = StructType([
    StructField("value", FloatType(), True),
    StructField("unit", IntegerType(), True),
    StructField("referenceDatum", IntegerType(), True)
])
 
ELEVATION_GEOID_SCHEMA = StructType([
    StructField("geoidHeight", FloatType(), True),
    StructField("hae", FloatType(), True)
])
 
AIRPORT_SCHEMA = StructType([
    StructField("_id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("type", IntegerType(), True),
    StructField("trafficType", ArrayType(IntegerType()), True),
    StructField("magneticDeclination", FloatType(), True),
    StructField("country", StringType(), True),
    StructField("geometry", GEOMETRY_SCHEMA, True),
    StructField("elevation", ELEVATION_SCHEMA, True),
    StructField("ppr", BooleanType(), True),
    StructField("private", BooleanType(), True),
    StructField("skydiveActivity", BooleanType(), True),
    StructField("winchOnly", BooleanType(), True),
    StructField("runways", ArrayType(StructType([])), True),
    StructField("createdAt", StringType(), True),
    StructField("updatedAt", StringType(), True),
    StructField("createdBy", StringType(), True),
    StructField("updatedBy", StringType(), True),
    StructField("elevationGeoid", ELEVATION_GEOID_SCHEMA, True),
    StructField("__v", IntegerType(), True),
    StructField("icaoCode", StringType(), True),
    StructField("iataCode", StringType(), True)
])
 
ENVELOPE_SCHEMA = StructType([
    StructField("limit", IntegerType(), True),
    StructField("totalCount", IntegerType(), True),
    StructField("totalPages", IntegerType(), True),
    StructField("page", IntegerType(), True),
    StructField("items", ArrayType(AIRPORT_SCHEMA), True)
])
 
# === 4. Spark Session ===
# La configuration des packages est fournie par la commande `spark-submit --packages ...`
spark = (
    SparkSession.builder
    .appName("AirportDataProcessingFull")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")
print("Spark Session initialisée.\n")
 
 
# === BLOC DE VÉRIFICATION CORRIGÉ ===
print("Vérification du contenu de la table PostgreSQL...")
try:
    # On utilise .jdbc() qui accepte le dictionnaire properties
    existing_data = spark.read.jdbc(
        url=PG_URL,
        table=PG_TABLE,
        properties=PG_PROPERTIES
    ).load()
 
    count = existing_data.count()
    if count > 0:
        print(f"✅ La table 'airports' contient déjà {count} lignes.")
        existing_data.show(5, truncate=False)
    else:
        print("ℹ️ La table 'airports' est vide pour le moment.")
 
except Exception as e:
    print(f"⚠️ Impossible de lire la table 'airports' (sera corrigé au batch 0): {e}")
 
 
# === 5. Lecture du flux Kafka ===
kafka_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
    .option("subscribe", KAFKA_TOPIC)
    .option("startingOffsets", "earliest") # Lit tout l'historique au démarrage
    .load()
)
 
# === 6. Transformation ===
processed_df = (
    kafka_df.selectExpr("CAST(value AS STRING)")
    .select(from_json(col("value"), ENVELOPE_SCHEMA).alias("data"))
    .select(explode(col("data.items")).alias("airport"))
    .select(
        col("airport._id").alias("airport_id"),
        col("airport.name").alias("name"),
        col("airport.icaoCode").alias("icao"),
        col("airport.iataCode").alias("iata"),
        col("airport.country").alias("country"),
        col("airport.geometry.coordinates")[0].alias("longitude"),
        col("airport.geometry.coordinates")[1].alias("latitude"),
        col("airport.type").alias("airport_type"),
        col("airport.elevation.value").alias("elevation_meters"),
        col("airport.magneticDeclination").alias("mag_declination"),
        col("airport.ppr").alias("ppr"),
        col("airport.private").alias("is_private"),
        col("airport.skydiveActivity").alias("skydive_activity"),
        col("airport.winchOnly").alias("winch_only"),
        size(col("airport.runways")).alias("runway_count"),
        col("airport.createdAt").alias("created_at"),
        col("airport.updatedAt").alias("updated_at"),
        col("airport.createdBy").alias("created_by"),
        col("airport.updatedBy").alias("updated_by"),
        col("airport.elevationGeoid.geoidHeight").alias("geoid_height"),
        col("airport.elevationGeoid.hae").alias("hae")
    )
    .filter(col("icao").isNotNull())
)
 
# === 7. Fonction d’écriture PostgreSQL (Logique de dé-duplication) ===
def write_to_postgres(df, epoch_id):
   
    print(f"\n--- Démarrage Batch {epoch_id} ---")
   
    # 1. Dédoubler le batch entrant (contre les doublons DANS le batch)
    unique_df = df.dropDuplicates(["airport_id"])
    count_received = df.count()
    count_unique = unique_df.count()
    print(f"Batch {epoch_id}: {count_received} lignes reçues, réduites à {count_unique} lignes uniques.")
 
    # Si le batch est vide après déduplication, on s'arrête là.
    if count_unique == 0:
        print(f"--- Batch {epoch_id}: Aucune donnée unique à traiter. ---")
        return
 
    # 2. Lire les IDs qui sont DÉJÀ dans Postgres
    print(f"Batch {epoch_id}: Tentative de lecture de la table '{PG_TABLE}' pour déduplication...")
    try:
        existing_ids_df = spark.read.jdbc(
            url=PG_URL,
            table=PG_TABLE,
            properties=PG_PROPERTIES
        ).select("airport_id").cache()
               
        count_existing = existing_ids_df.count()
        print(f"Batch {epoch_id}: LECTURE PG RÉUSSIE. {count_existing} IDs existants trouvés.")
       
    except Exception as e:
        # Gère le cas où la table est vide au Batch 0
        print(f"Batch {epoch_id}: Table 'airports' non trouvée ou vide (erreur: {e}), je vais tout insérer.")
        existing_ids_df = spark.createDataFrame([], StructType([StructField("airport_id", StringType(), True)]))
 
    # 3. Filtrer pour ne garder que les NOUVELLES lignes (jointure "anti")
    new_rows_df = unique_df.join(
        existing_ids_df,
        unique_df["airport_id"] == existing_ids_df["airport_id"],
        "left_anti"
    )
 
    # 4. Écrire uniquement les nouvelles lignes
    new_rows_count = new_rows_df.count()
   
    if new_rows_count > 0:
        print(f"--- Writing batch {epoch_id} to PostgreSQL ---")
        try:
            new_rows_df.write.jdbc(
                url=PG_URL,
                table=PG_TABLE,
                mode="append",
                properties=PG_PROPERTIES
            )
            print(f"--- Batch {epoch_id} successfully written ---")
            print(f"Insertion des nouvelles données dans PostgreSQL terminée ({new_rows_count} lignes ajoutées).")
       
        except Exception as e:
            print(f"ERREUR PENDANT L'ÉCRITURE: {e}")
            pass
    else:
        print(f"--- Batch {epoch_id}: Aucune nouvelle ligne à insérer (0 lignes ajoutées) ---")
 
    existing_ids_df.unpersist()
 
 
# === 8. Lancement du Stream ===
query = (
    processed_df.writeStream
    .foreachBatch(write_to_postgres)
    .outputMode("append")
    .trigger(processingTime="30 seconds")
    .start()
)
 
print("Streaming vers PostgreSQL démarré...")
query.awaitTermination()
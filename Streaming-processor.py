import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, explode, size # Import 'size' function
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType, IntegerType, LongType,
    ArrayType, DoubleType, BooleanType # Added BooleanType
)
 
# --- 1. Configuration des Paquets ---
KAFKA_VERSION = 3.5.0
POSTGRES_VERSION = 42.7.3
 
KAFKA_PACKAGES = forg.apache.sparkspark-sql-kafka-0-10_2.12{KAFKA_VERSION}
POSTGRES_PACKAGES = forg.postgresqlpostgresql{POSTGRES_VERSION}
 
# --- 2. Définition des Schémas ---
 
# Schéma 2a  Structures imbriquées
GEOMETRY_SCHEMA = StructType([
    StructField(type, StringType(), True),
    StructField(coordinates, ArrayType(DoubleType()), True) # [lon, lat]
])
 
ELEVATION_SCHEMA = StructType([
    StructField(value, FloatType(), True),
    StructField(unit, IntegerType(), True),
    StructField(referenceDatum, IntegerType(), True)
])
 
ELEVATION_GEOID_SCHEMA = StructType([ # Ajouté
    StructField(geoidHeight, FloatType(), True),
    StructField(hae, FloatType(), True)
])
 
# Schéma 2b  L'aéroport individuel (beaucoup plus complet)
AIRPORT_SCHEMA = StructType([
    StructField(_id, StringType(), True),
    StructField(name, StringType(), True),
    StructField(type, IntegerType(), True),
    StructField(trafficType, ArrayType(IntegerType()), True), # Gardé comme tableau
    StructField(magneticDeclination, FloatType(), True),
    StructField(country, StringType(), True),
    StructField(geometry, GEOMETRY_SCHEMA, True),
    StructField(elevation, ELEVATION_SCHEMA, True),
    StructField(ppr, BooleanType(), True), # Ajouté
    StructField(private, BooleanType(), True), # Ajouté
    StructField(skydiveActivity, BooleanType(), True), # Ajouté
    StructField(winchOnly, BooleanType(), True), # Ajouté
    StructField(runways, ArrayType(StructType([])), True), # Structure vide pour pouvoir compter
    StructField(createdAt, StringType(), True), # Gardé comme String
    StructField(updatedAt, StringType(), True), # Gardé comme String
    StructField(createdBy, StringType(), True), # Ajouté
    StructField(updatedBy, StringType(), True), # Ajouté
    StructField(elevationGeoid, ELEVATION_GEOID_SCHEMA, True), # Ajouté
    StructField(__v, IntegerType(), True), # Ajouté
    StructField(icaoCode, StringType(), True), # Nom API original
    StructField(iataCode, StringType(), True), # Nom API original
    # On ignore frequencies, altIdentifier, services, contact, images, remarks, hoursOfOperation pour l'instant
])
 
# Schéma 2c  L'enveloppe JSON complète
ENVELOPE_SCHEMA = StructType([
    StructField(limit, IntegerType(), True),
    StructField(totalCount, IntegerType(), True),
    StructField(totalPages, IntegerType(), True),
    StructField(page, IntegerType(), True),
    StructField(items, ArrayType(AIRPORT_SCHEMA), True)
])
 
# --- 3. Initialisation de la SparkSession ---
spark = (
    SparkSession.builder
    .appName(AirportDataProcessingFull) # Nom mis à jour
    .config(spark.jars.packages, f{KAFKA_PACKAGES},{POSTGRES_PACKAGES})
    .getOrCreate()
)
spark.sparkContext.setLogLevel(WARN)
print(Spark Session créée et configurée.)
 
# --- 4. Lecture du Flux Kafka ---
kafka_df = (
    spark.readStream
    .format(kafka)
    .option(kafka.bootstrap.servers, kafka9093) # Port INTERNE
    .option(subscribe, airports)
    .option(startingOffsets, latest) # Garder latest pour éviter OOM
    .load()
)
 
# --- 5. Transformation ---
processed_df = (
    kafka_df.selectExpr(CAST(value AS STRING))
    .select(from_json(col(value), ENVELOPE_SCHEMA).alias(data))
    .select(explode(col(data.items)).alias(airport))
    .select(
        col(airport._id).alias(airport_id),
        col(airport.name).alias(name),
        col(airport.icaoCode).alias(icao),
        col(airport.iataCode).alias(iata),
        col(airport.country).alias(country),
        col(airport.geometry.coordinates)[0].alias(longitude),
        col(airport.geometry.coordinates)[1].alias(latitude),
        col(airport.type).alias(airport_type),
        col(airport.elevation.value).alias(elevation_meters),
        col(airport.magneticDeclination).alias(mag_declination),
        col(airport.ppr).alias(ppr),
        col(airport.private).alias(is_private), # Renommer pour éviter conflit SQL
        col(airport.skydiveActivity).alias(skydive_activity),
        col(airport.winchOnly).alias(winch_only),
        size(col(airport.runways)).alias(runway_count), # Compter les pistes
        col(airport.createdAt).alias(created_at),
        col(airport.updatedAt).alias(updated_at),
        col(airport.createdBy).alias(created_by),
        col(airport.updatedBy).alias(updated_by),
        col(airport.elevationGeoid.geoidHeight).alias(geoid_height),
        col(airport.elevationGeoid.hae).alias(hae) # Height Above Ellipsoid
    )
    .filter(col(icao).isNotNull()) # Garder un filtre pertinent
)
 
# TEST Afficher le contenu du DataFrame dans la console Spark
debug_query = (
    processed_df.writeStream
    .outputMode(append)
    .format(console)
    .option(truncate, false)
    .trigger(processingTime=15 seconds) # Moins fréquent que l'écriture DB
    .start()
)
 
 
# --- 6. Écriture (Sink) - Vers PostgreSQL ---
PG_URL = jdbcpostgresqlpostgres5432mydb
PG_TABLE = airports
PG_PROPERTIES = {
    user admin,
    password admin,
    driver org.postgresql.Driver
}
 
def write_to_postgres(df, epoch_id)
    print(f--- Writing batch {epoch_id} to PostgreSQL ---)
    try # -- Uncomment this
        df.write 
          .jdbc(url=PG_URL, table=PG_TABLE, mode=append, properties=PG_PROPERTIES)
        print(f--- Batch {epoch_id} successfully written ---)
    except Exception as e # -- Uncomment this
        # Optional Log the specific error if needed, but 'pass' ignores it
        print(f--- INFO Ignoring error in batch {epoch_id} (likely duplicate key) {e} ---) # -- Uncomment or modify print
        pass # -- Uncomment this (This ignores the error)
 
query = (
    processed_df.writeStream
    .foreachBatch(write_to_postgres)
    .outputMode(append)
    .trigger(processingTime=30 seconds)
    .start()
)
 
print(Streaming vers PostgreSQL démarré (avec plus de champs)...)
query.awaitTermination()
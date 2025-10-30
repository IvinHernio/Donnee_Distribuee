version: '3.1'
 
services:
  # ZOOKEEPER
  zookeeper:
    image: wurstmeister/zookeeper
    container_name: zookeeper
    ports:
      - "2181:2181"
    networks:
      - bigdata-net
 
# KAFKA
  kafka:
    image: wurstmeister/kafka:latest
    container_name: kafka
    ports:
      - "9092:9092" # Port EXTERNE (pour Offset Explorer sur votre PC)
      - "9093:9093" # Port INTERNE (pour NiFi et Spark dans Docker)
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_BROKER_ID: 1
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
 
      # --- Configuration pour double accès (Docker + Hôte) ---
      KAFKA_LISTENERS: "INTERNAL://:9093,EXTERNAL://:9092"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka:9093,EXTERNAL://localhost:9092"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: "INTERNAL"
      # --- Fin de la configuration ---
 
      # Vos paramètres de taille de message (conservés)
      KAFKA_MESSAGE_MAX_BYTES: 52428800
      KAFKA_REPLICA_FETCH_MAX_BYTES: 52428800
      KAFKA_MAX_REQUEST_SIZE: 52428800
      KAFKA_SOCKET_REQUEST_MAX_BYTES: 52428800
    depends_on:
      - zookeeper
    networks:
      - bigdata-net
 
    #NIFI
  nifi:
    image: apache/nifi:1.28.0
    container_name: nifi
    ports:
      - "8443:8443"
    environment:
      NIFI_WEB_HTTPS_HOST: "0.0.0.0"
      NIFI_WEB_HTTPS_PORT: "8443"
      NIFI_WEB_PROXY_HOST: "localhost:8443"
    depends_on:
      - kafka
    networks:
      - bigdata-net
 
  # SPARK MASTER (Image officielle Apache Spark 3.5.0)
  spark-master:
    image: apache/spark:3.5.0
    container_name: spark-master
    command: /opt/spark/bin/spark-class org.apache.spark.deploy.master.Master --host spark-master
    ports:
      - "7077:7077"
      - "8081:8080"  # Interface Web Spark : Mappé à 8081 sur l'hôte
    networks:
      - bigdata-net
    volumes:
      - ./spark-job:/opt/spark-apps
 
  # SPARK WORKER (Image officielle Apache Spark 3.5.0)
  spark-worker:
    image: apache/spark:3.5.0
    container_name: spark-worker
    command: /opt/spark/bin/spark-class org.apache.spark.deploy.worker.Worker spark://spark-master:7077
    depends_on:
      - spark-master
    networks:
      - bigdata-net
    volumes:
      - ./spark-job:/opt/spark-apps
 
  # POSTGRESQL
  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
    networks:
      - bigdata-net
 
  # PGADMIN (Interface graphique pour Postgres)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: "admin@example.com" # Email de connexion pour pgAdmin
      PGADMIN_DEFAULT_PASSWORD: "admin"         # Mot de passe pour pgAdmin
    ports:
      - "5050:80" # Accès web pgAdmin sur http://localhost:5050
    depends_on:
      - postgres
    networks:
      - bigdata-net
 
  # GRAFANA
  grafana:
    image: grafana/grafana-enterprise:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
    depends_on:
      - postgres
    volumes:
      - ./grafana_data:/var/lib/grafana
    networks:
      - bigdata-net
 
# Réseau commun
networks:
  bigdata-net:
    driver: bridge
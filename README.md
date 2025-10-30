# Projet Données Distribuées — Pipeline Big Data

## 🧠 Objectif du projet

Ce projet a pour but de **mettre en place un pipeline de traitement distribué de données aéronautiques** en temps réel, en s'appuyant sur un écosystème Big Data complet :  
**NiFi → Kafka → Spark → PostgreSQL → Grafana**.

L’objectif est de :
- Collecter des données d’aéroports ou de vols via une API open source (comme AviationStack ou OpenAIP).
- Ingest ces données dans Kafka à l’aide d’un flux NiFi.
- Traiter et nettoyer les flux en temps réel avec **Apache Spark Structured Streaming**.
- Stocker les résultats dans une base de données **PostgreSQL** accessible via **pgAdmin**.
- Restituer les données récoltées via **Grafana**.

---

## ⚙️ Architecture technique

(Image/StructureProjet.png)


## 🧩 Technologies utilisées

|Logo| Composant | Technologie | Rôle |
|----|-----------|-------------|------|
|(Image/NIFI.png)| **NiFi** | apache nifi:1.28.0 | Collecte et routage des données depuis l’API |
|(Image/KAFKA.png)| **Kafka** | Apache Kafka 3.5 | File de messages pour la diffusion temps réel |
|(Image/SPARK.png)| **Spark** | apache spark:3.5.0 | Traitement et transformation des données |
|(Image/PgAdmin.png)| **PostgreSQL** | PostgreSQL 15 | Stockage persistant et structuré |
|(Image/PgAdmin.png)| **pgAdmin** | Interface web | Consultation et gestion de la base de données |
|(Image/DOCKER.png)| **Docker Compose** | Orchestration | Démarrage automatisé de tous les services |
|(Image/GRAFANA.png)| **Grafana** | grafana-enterprise:latest | Restitution graphique |

---

## 🐳 Démarrage du projet

### Docker Compose :

(docker-compose.py)

### 2️⃣ Accès aux interfaces :

| Service      | URL                        |
|-------------|----------------------------|
| NIFI        | [https://localhost:8443/nifi](https://localhost:8443/nifi) |
| PgAdmin     | [http://localhost:5050](http://localhost:5050) |
| Spark Master| [http://localhost:8080](http://localhost:8080) |
| Grafana     | [http://localhost:3000](http://localhost:3000) |

### (Image/NIFI.png) | 1️⃣ Récupération des données avec Apache NiFi :
- **Rôle :** Collecte et routage des données depuis les API aéronautiques.  
- Connecteurs vers différentes APIs.  
- Prétraitement léger (filtrage, enrichissement).  
- Envoi vers Kafka pour diffusion en temps réel.  

(Image/StructureNIFI.png)

- InvokeHTTP : **Connexion à l’API** externe pour récupérer les données aéronautiques.
- EvaluateJsonPath : **Analyse le JSON** reçu pour extraire les champs spécifiques
- AttributesToJSON : **Convertit les attributs** NiFi extraits en nouveau flux JSON structuré
- PublishKafkaRecord : Envoie les données transformées **vers un topic Kafka**
- LogAttribute : **Composant de debug** et de suivi

### (Image/KAFKA.png) | 2️⃣ Apache Kafka
- **Rôle :** File de messages pour diffuser les données en temps réel.  
- Producteurs : NiFi envoie les données.  
- Topics : organisent les flux par type de données.  
- Consommateurs : Spark récupère les données pour traitement. 

### (Image/SPARK.png) | 3️⃣ Apache Spark (Structured Streaming)
- **Rôle :** Traitement et nettoyage des flux en temps réel.  
- Calculs sur flux en continu.  
- Nettoyage, transformation et agrégation des données. 

Afin de réaliser les traitements, un fichier PySpark a été crée : **Streaming-processor**
Ce script gère le traitement en temps réel des données d’aéroports provenant de Kafka, avant de les insérer dans PostgreSQL.

Voici les grandes étapes du pipeline Spark :

| 🧩 Étape | ⚙️ Fonction | 🧠 Description |
|:--:|:--|:--|
| 1️⃣ | **Configuration** | Charge les dépendances **Kafka** et **PostgreSQL** |
| 2️⃣ | **Schémas** | Décrit la structure des **données d’aéroports** |
| 3️⃣ | **SparkSession** | Initialise **Spark** avec les bons connecteurs |
| 4️⃣ | **Lecture** | Récupère les **données JSON** depuis **Kafka** |
| 5️⃣ | **Transformation** | Nettoie et **normalise les champs importants** |
| 6️⃣ | **Debug** | Affiche les **données dans la console** |
| 7️⃣ | **Écriture** | Insère les **aéroports dans PostgreSQL** |
| 8️⃣ | **Exécution** | Laisse le **streaming tourner en continu** |

(Streaming-processor.py)


### 4️⃣ PostgreSQL + pgAdmin
- **Rôle :** Stockage persistant et gestion de la base de données.  
- pgAdmin pour explorer les tables et exécuter des requêtes.

### 5️⃣ Grafana
- **Rôle :** Visualisation graphique des données en temps réel.  
- **Fonctionnalités principales :**  
  - Création de **dashboards** pour représenter les données d’aéroports.  
  - Graphiques, alertes et indicateurs clés (**KPI**).
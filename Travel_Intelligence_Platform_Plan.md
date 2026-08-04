
# Travel Intelligence Platform (TIP)

## Plataforma Inteligente de Ingeniería de Datos, Analítica e IA para el Sector Turístico

### Problema
Actualmente la información relevante para el sector turismo se encuentra distribuida en múltiples fuentes:
- Clima
- Información geográfica
- Información turística
- Información económica
- Información demográfica

La plataforma automatiza la integración, limpieza, análisis y explotación de estos datos para apoyar la toma de decisiones.

---

## Alcance (Fase 1 — Perú)

El MVP se enfoca únicamente en Perú: se monitorean las capitales de departamento (~25 ciudades) con datos públicos y gratuitos. Un alcance mundial se descarta en esta fase por el volumen de datos y la complejidad que exige; Perú permite validar toda la arquitectura con un dataset controlado.

- Países: 1 (Perú)
- Ciudades: ~25 capitales de departamento
- Fuentes: APIs públicas y datasets estáticos
- Infraestructura: 100% serverless en AWS

---

# Objetivos

## Objetivo General

Desarrollar una plataforma cloud-native capaz de integrar múltiples fuentes de datos públicas mediante procesos ETL, generar un Data Lake, normalizar información heterogénea, construir indicadores analíticos y apoyar la toma de decisiones mediante Machine Learning e Inteligencia Artificial.

## Objetivos Específicos

- Automatizar la extracción de datos.
- Integrar múltiples APIs.
- Implementar procesos ETL.
- Construir un Data Lake.
- Construir un Data Warehouse.
- Generar dashboards.
- Aplicar Machine Learning.
- Incorporar IA Generativa.
- Utilizar una arquitectura Serverless en AWS.
- Implementar una arquitectura de software hexagonal, modular y por capas.

---

# Stack Tecnológico

## Frontend

- React + Vite
- TypeScript
- Tailwind CSS
- TanStack Query
- Apache ECharts (o Recharts)
- Leaflet (react-leaflet)
- React Router
- shadcn/ui (o librería de componentes similar)
- Despliegue: estático en S3 + CloudFront

## Backend

- FastAPI (empaquetado en AWS Lambda vía Mangum)
- Python
- Pydantic v2
- SQLAlchemy 2 + Alembic (migraciones)
- pytest, ruff
- Arquitectura Hexagonal (puertos y adaptadores), modular por capas

## Base de Datos

- PostgreSQL (Amazon RDS, db.t3.micro para el MVP)
- RDS Proxy (o PgBouncer) para el pool de conexiones con Lambda
- Athena para consultar S3 (Parquet) sin cargar todo a PostgreSQL

## Cloud (AWS)

- API Gateway
- Lambda
- EventBridge
- S3 (Data Lake)
- Athena (consultas sobre S3/Parquet)
- RDS (PostgreSQL) + RDS Proxy
- CloudFront (frontend estático)
- CloudWatch
- Secrets Manager (claves de API: Groq, ExchangeRate)
- SAM o CDK (Infraestructura como Código)
- Groq (IA Generativa — API gratuita)

---

# APIs y Fuentes de Datos

## Open-Meteo
- Temperatura
- Humedad
- Lluvia
- Viento

## REST Countries
- País
- Idioma
- Moneda
- Región
- Bandera
- Fase 1: uso mínimo (país fijo: Perú); cobra relevancia al crecer a otros países.

## Dataset Perú (reemplaza a GeoDB Cities)
- Dataset estático de capitales de departamento de Perú
- Población y coordenadas
- Fuente: GeoNames (o dataset nacional) sembrado en PostgreSQL

## OpenStreetMap (Overpass API)
- Hoteles
- Restaurantes
- Museos
- Parques
- Hospitales
- Estrategia Fase 1: consultas por bounding box de Perú o por ciudad, solo las categorías necesarias y caché de resultados en S3 para no re-consultar ni superar los límites de ancho de banda.

## ExchangeRate API
- Tipo de cambio

## OpenTripMap
- POIs turísticos (atracciones, museos, parques) con fotos y descripciones en español
- Complementa a Overpass; API key gratuita con cuota diaria

## Nominatim (OSM)
- Geocoding: de nombre de ciudad/lugar a coordenadas
- Gratis (1 solicitud/seg)

## Wikipedia Pageviews API
- Visitas por artículo de cada ciudad/atracción a lo largo del tiempo
- Proxy de interés/demanda turística → alimenta el módulo de Predicción

## MediaWiki API (Wikipedia + Wikivoyage)
- Descripciones, historia y guías de cada ciudad
- Contenido para el AI Assistant (Groq)

## Google Trends (pytrends)
- Evolución de búsquedas por destino en el tiempo
- Gratis; refuerza la demanda turística

## World Bank API
- Indicadores económicos (PIB, llegadas de turistas) por país
- Gratis

## Datos Abiertos Perú (MINCETUR e INEI)
- Estadísticas oficiales de turismo y demografía peruana (datasets descargables)
- Alineado con el alcance Perú

## Google AI Studio (Gemini)
- API gratuita como respaldo de Groq y para embeddings (RAG del AI Assistant)

## Hugging Face Inference API
- Free tier para modelos de embeddings y clasificación

## Groq API
- Inferencia de LLM para la IA Generativa (ej. Llama 3.3)
- API gratuita con límites suficientes para el MVP

### Nota sobre APIs "gratuitas"
Booking, Skyscanner, TripAdvisor y Google Places **no tienen tier gratuito real** (Google Places cobra, TripAdvisor exige partnership). Amadeus Self-Service sí ofrece entorno de pruebas gratuito.

### Futuras Integraciones

- Amadeus (entorno de pruebas gratuito)
- Booking
- Skyscanner
- Google Places
- TripAdvisor

### Fuentes en Evaluación (por decidir)

Documentadas como candidatas, pero **se decide en el momento de implementar** si se integran vía API, dataset estático o se descartan:

**Vuelos:**
- Amadeus Self-Service (entorno de pruebas gratuito): rutas, aerolíneas y precios de referencia.
- AviationStack (free tier): schedules y estado de vuelos.
- OpenFlights / OurAirports: datasets estáticos de aerolíneas, aeropuertos y rutas.

**Buses (Perú):**
- No existe API pública gratuita para rutas interprovinciales.
- Opción: dataset estático curado (empresa, ruta, duración, precio aprox.) con actualización manual o futuras alianzas (RedBus/Clickbus).

**Seguridad y eventos:**
- US State Dept / UK FCDO: travel advisories gratuitos → safety score por destino.
- Eventbrite / SeatGeek: eventos locales por ciudad.

**Contexto de demanda:**
- Festivos y temporada escolar del Perú (dataset estático).
- Conectividad: Lima como hub obliga a comparar tiempos por avión vs bus.

**UI:**
- Unsplash API (tier gratis): fotos de ciudades para el dashboard.

---

# Arquitectura

```text
APIs y Fuentes
 ├── Open-Meteo (clima)
 ├── Overpass + OpenTripMap (POIs, bbox Perú)
 ├── ExchangeRate (tipo de cambio)
 ├── Nominatim (geocoding)
 ├── Wikipedia / Wikivoyage + Pageviews (contenido y demanda)
 ├── World Bank + Datos Abiertos Perú (económicos/demográficos)
 ├── Dataset Perú (ciudades y población)
 └── Groq + Gemini (LLM)

        │
        ▼
Data Ingestion (AWS Lambda)
        │
        ▼
S3 Bronze (Raw JSON)
        │
        ▼
ETL
 ├── Limpieza
 ├── Validación
 ├── Normalización
 ├── Conversión
 └── Enriquecimiento
        │
        ▼
S3 Silver
        │
        ▼
S3 Gold (modelos)  ──►  PostgreSQL (fuente de verdad)
        │
        ▼
Backend FastAPI (Lambda / Mangum — Hexagonal)
        │
        ▼
Analytics
        │
        ├── KPIs
        ├── Rankings
        ├── Heatmaps
        ├── Series Temporales
        └── Mapas
        │
        ▼
Machine Learning
        │
        ▼
IA Generativa (Groq)
```

---

# Arquitectura de Software (Hexagonal)

El backend se organiza de forma **modular y por capas** siguiendo Arquitectura Hexagonal (puertos y adaptadores), lo que desacopla la lógica de negocio de los detalles técnicos:

- **Dominio**: entidades, reglas de negocio y el *Tourism Score* (sin dependencias externas).
- **Aplicación**: casos de uso, orquestación de servicios y puertos (interfaces).
- **Infraestructura**: adaptadores concretos — AWS Lambda, S3, PostgreSQL, APIs externas, Groq.

Cada fuente de datos externa (Open-Meteo, Overpass, ExchangeRate, Groq) es un adaptador; cambiar o agregar una fuente no altera el dominio.

---

# Estructura del Proyecto (Monorepo)

```text
GEO-TOUR-WP/
├── infra/            # SAM/CDK: Lambda, S3, API Gateway, EventBridge, RDS, CloudFront
├── backend/          # FastAPI hexagonal
│   ├── domain/            # entidades y reglas de negocio (Tourism Score)
│   ├── application/       # casos de uso y puertos (interfaces)
│   └── infrastructure/    # adaptadores (S3, PostgreSQL, APIs externas)
├── etl/              # Lambdas de pipeline (una por fuente) + librería compartida
├── ml/               # notebooks, entrenamiento y artefactos
├── frontend/         # React + Vite (S3 + CloudFront)
└── shared/           # modelos Pydantic / SQLAlchemy compartidos
```

Nota: el pipeline ETL es procesamiento por lotes y no vive dentro del hexágono; la arquitectura hexagonal aplica al backend API que sirve datos al dashboard.

---

# ETL

## Extract
- Consumir APIs.
- Overpass: consultas acotadas por bounding box (Perú/ciudad) y por categoría; caché de resultados en S3.
- Procesamiento incremental: guardar `last_sync` por fuente para no re-consultar todo en cada corrida.
- Guardar JSON originales en S3 (Bronze).

## Transform

### Limpieza
- Eliminar duplicados.
- Eliminar registros inválidos.
- Eliminar campos innecesarios.

### Normalización
- PE → Perú
- Republic of Peru → Perú
- LIMA → Lima

### Conversión
- Monedas
- Fechas
- Coordenadas
- Temperaturas

### Validación
- Campos obligatorios
- Tipos de datos
- Valores nulos

### Enriquecimiento
Combinar datos provenientes de diferentes APIs.

## Load

- S3 Silver
- S3 Gold (Parquet, particionado por fecha — consultable con Athena)
- PostgreSQL (fuente de verdad para el dashboard)

---

# Data Lake

## Bronze
Datos originales sin modificar.

## Silver
Datos limpios y normalizados.

## Gold
Datos listos para modelos.

## Roles
- S3 Gold: datasets finales (Parquet/JSON) para procesos de Machine Learning, particionados por fecha y consultables con Athena.
- PostgreSQL: fuente de verdad para el dashboard y consultas analíticas.

---

# Modelo de Datos (Star Schema)

En PostgreSQL:

- `dim_city`: ciudades, departamento, coordenadas, población.
- `dim_date`: calendario (día, mes, año, estación).
- `dim_poi_category`: categorías de puntos de interés (hoteles, restaurantes, museos, parques, hospitales).
- `fact_daily_city`: métricas diarias por ciudad (clima, conteos de POI, tipo de cambio).
- `fact_tourism_score`: puntaje de atractivo turístico por ciudad y fecha.

---

# Big Data

Conceptos cubiertos:

- Data Lake
- Arquitectura Medallion
- ETL
- Integración de datos
- Datos heterogéneos
- Procesamiento incremental
- Arquitectura Serverless
- Escalabilidad
- Automatización

---

# Machine Learning

## Tourism Score

Variables:
- Hoteles
- Restaurantes
- Museos
- Parques
- Clima
- Población

Resultado:
- Puntaje de atractivo turístico.

Fase 1: fórmula con pesos (regla de negocio) implementada en el dominio del hexágono.
Fase 2: refinar el scoring con Machine Learning.

## Clustering
Agrupar ciudades similares (primera técnica de ML a implementar).

## Clasificación
- Excelente
- Bueno
- Regular

## Predicción
Demanda turística.

---

# IA Generativa

Motor: **Groq** (API gratuita, modelos Llama 3.x).

Consultas en lenguaje natural:

- ¿Qué ciudad es mejor para visitar este mes?
- ¿Qué destinos crecieron más?
- Resume los cambios de la última sincronización.
- ¿Qué país tiene mejores condiciones climáticas?

---

# Dashboard

## Módulos

- Dashboard Ejecutivo
- ETL Manager
- Data Sources
- Data Explorer
- Analytics
- Machine Learning
- AI Assistant
- Configuración

## KPIs

- Países monitoreados
- Ciudades
- Hoteles
- Restaurantes
- Museos
- Clima promedio
- Tourism Score

---

# Roles y Flujos de Usuario

El sistema se concibe como un producto ya comercializado: trabajamos como una agencia de viajes que usa la plataforma para operar y asesorar a sus clientes. Hay **tres roles** con control de acceso basado en permisos (RBAC); el frontend renderiza solo los módulos permitidos según el rol.

| Rol | Acceso | Uso típico |
|-----|--------|-----------|
| **Admin** | Todo (datos + ML + configuración) | Dueño del sistema: fuentes, ETL, usuarios, exploración y análisis de datos |
| **Ejecutivo** | Dashboard + IA | Toma de decisiones: KPIs y preguntas al AI Assistant |
| **Agente de viajes** | Consulta de destinos | Asesorar clientes: buscar, comparar y recomendar ciudades |

## Flujo de acceso

```
Login (Cognito) → JWT → API Gateway valida el token → FastAPI verifica el rol → Frontend muestra solo los módulos autorizados
```

## Matriz de permisos por módulo

| Módulo | Admin | Ejecutivo | Agente |
|--------|:-----:|:---------:|:------:|
| Dashboard Ejecutivo | ✅ | ✅ | ✅ |
| Mapa y búsqueda de ciudades | ✅ | ✅ | ✅ |
| Data Explorer (Athena) | ✅ | — | — |
| Analytics y exportación | ✅ | ✅ | — |
| Machine Learning | ✅ | — | — |
| AI Assistant | ✅ | ✅ | — |
| ETL Manager (corridas y estados) | ✅ | — | — |
| Data Sources (configuración) | ✅ | — | — |
| Configuración y usuarios | ✅ | — | — |

## Flujos por rol

### Admin
Configurar fuentes de datos y sus límites → Programar corridas (EventBridge) o sync manual → Monitorear estado de ETL y calidad de datos → Gestionar usuarios y permisos → Explorar el dataset (Data Explorer vía Athena) → Filtrar y exportar CSV → Ver clustering y Tourism Score → Detectar anomalías de calidad y reportarlas.

### Ejecutivo
Abrir el dashboard → Revisar KPIs (ciudades, clima, scores) → Preguntar al AI Assistant ("¿Qué ciudad conviene más este mes?") → Descargar reporte para la agencia.

### Agente de viajes
Buscar una ciudad → Ver tourism score, clima, POIs y mapa → Comparar 2-3 ciudades → Recomendar el destino al cliente final.

---

# Flujo Completo

```text
EventBridge
    ↓
Lambda
    ↓
Consumir APIs (Open-Meteo, Overpass, OpenTripMap, ExchangeRate, Wikipedia, Dataset Perú)
    ↓
S3 Bronze
    ↓
ETL
    ↓
S3 Silver
    ↓
S3 Gold
    ↓
PostgreSQL
    ↓
Backend FastAPI (Hexagonal)
    ↓
Dashboard
    ↓
Machine Learning
    ↓
IA Generativa (Groq)
```

---

# Data Quality Engine

Se ejecuta como un Lambda post-ETL que escribe las métricas de calidad en PostgreSQL y CloudWatch (para alertas).

Métricas:

- Completitud
- Consistencia
- Duplicidad
- Validez
- Freshness

Ejemplo:

| Fuente | Calidad | Estado |
|--------|---------:|:------|
| Open-Meteo | 99% | 🟢 |
| REST Countries | 100% | 🟢 |
| Dataset Perú | 96% | 🟢 |
| OpenStreetMap | 91% | 🟡 |
| OpenTripMap | 90% | 🟡 |

---

# Conceptos Cubiertos

| Área | Conceptos |
|------|-----------|
| Big Data | Data Lake, Medallion, Escalabilidad |
| ETL | Extract, Transform, Load |
| Data Engineering | Pipelines, Conectores, Automatización |
| Arquitectura de Software | Hexagonal, Capas, Modularidad |
| Cloud | AWS Lambda, S3, EventBridge, API Gateway |
| Data Warehouse | PostgreSQL |
| Machine Learning | Clustering, Predicción, Clasificación |
| IA | LLM, Consultas, Reportes |
| Visualización | Dashboards, KPIs, Mapas |

---

# Estrategia de Desarrollo (Local-First) y Costos

Desarrollo y pruebas 100% locales (sin gasto). AWS se usa solo para demos e integración final.

## Entorno local (gratis)

- Docker + PostgreSQL local
- LocalStack (emula Lambda, S3, API Gateway, Secrets Manager, EventBridge)
- SAM Local: corre las Lambdas en Docker como en AWS
- DuckDB: emula Athena consultando Parquet local
- APIs públicas (Open-Meteo, Overpass, OpenTripMap, Wikipedia) llamadas directas

## Flujo de trabajo

```text
Desarrollo local (Docker + LocalStack + DuckDB) → $0
    ↓
CI/CD (GitHub Actions, tests contra LocalStack) → $0
    ↓
Despliegue a AWS solo para demo/integración → ~$0-15/mes
```

## Costos estimados

| Servicio | Free Tier | Después de 12 meses |
|----------|-----------|---------------------|
| Lambda | 1M req/mes (siempre gratis) | ≈ $0 |
| S3 | 5 GB (siempre gratis) | ≈ $0 |
| EventBridge | 14M invocaciones/mes | ≈ $0 |
| API Gateway | 1M req/mes (12 meses) | ~$3.50/M |
| CloudWatch | 5 GB logs + 10 alarmas | bajo |
| RDS (PostgreSQL) | t3.micro, 750 h/mes (12 meses) | ~$15/mes |
| Athena | no cubierto | ~$5/TB (volumen Perú ≈ centavos) |
| **Total** | **~$0/mes** | **~$15-20/mes** |

## Reglas de gasto

- Billing alerts desde el día 1.
- PostgreSQL local para desarrollo; RDS solo para staging/demo.
- DuckDB reemplaza a Athena en local (no pagar consultas innecesarias).

---

# Roadmap de Implementación (Fases y Mejores Prácticas)

Cada fase entrega algo funcional y se valida **en local** antes de tocar AWS. El orden minimiza riesgo: primero los ETL simples, luego el riesgo mayor (Overpass), y el ML/IA al final cuando ya hay datos acumulados.

> **Estado actual (ago 2026):** Fases 0, 1, 2 y 3 completadas en local (monorepo, star schema, ETL Open-Meteo/ExchangeRate y ETL diario de POIs con 25 ciudades + 13 sitios famosos, 24 categorías). Siguiente: Fase 4 (backend hexagonal).

## Fase 0 — Base del proyecto
- **Objetivo**: repositorio y entorno local listos.
- **Entregables**: `git init` + `.gitignore`, docker-compose (PostgreSQL), estructura del monorepo, ruff + pytest configurados.
- **Mejores prácticas**: commits pequeños, ramas `main`/`dev`/`feat/*`, PR obligatorio, secrets nunca en el repo.

## Fase 1 — Infraestructura base
- **Objetivo**: S3 y seed del Dataset Perú.
- **Entregables**: LocalStack con buckets, seed de ~25 ciudades, esquema star schema con Alembic.
- **Mejores prácticas**: infraestructura como código desde el inicio (SAM/CDK), migraciones versionadas, seeds idempotentes.

## Fase 2 — ETL simples (Open-Meteo + ExchangeRate)
- **Objetivo**: pipeline Bronze → Silver → PostgreSQL funcionando.
- **Entregables**: Lambdas corriendo con SAM Local, JSON crudo en S3 (LocalStack), datos en PostgreSQL.
- **Mejores prácticas**: ETL idempotente, `last_sync` por fuente, logging estructurado, tests unitarios del transform.

## Fase 3 — Overpass / OpenTripMap (POIs)
- **Objetivo**: ETL diario de POIs con diseño robusto (no adivinar categorías).
- **Entregables**: captura amplia por bounding box por ciudad (tourism/historic/leisure/natural/amenity), consultas por clave para evitar timeouts, failover entre servidores Overpass, caché en S3, clasificación en 24 categorías de negocio que crecen con datos reales, alerta `sin_clasificar`, carga en `fact_poi_city`, y **catálogo curado de sitios famosos fuera del bbox de su ciudad** (Machu Picchu, Misti, Titicaca, Colca, etc.) con soporte multi-punto.
- **Mejores prácticas**: validar categorías y volúmenes primero; caché en S3; reintentos y failover; snapshot diario en la BD (sin filas fantasma); censos periódicos del `sin_clasificar` para descubrir categorías nuevas.

### Catálogo de sitios famosos (a futuro — panel de Admin)
El catálogo curado de sitios se alimentará **manualmente desde el panel de Admin** cuando exista el frontend. Para eso, el catálogo debe vivir en un **archivo YAML/JSON separado** (no en código) que el ETL lea al arrancar:
- **Búsqueda**: en el panel, el Admin busca un lugar por nombre (Nominatim/Overpass), revisa las coincidencias (nombre, etiquetas, coordenadas) y lo selecciona.
- **Alta**: el lugar se agrega al catálogo con su ciudad de atribución y radio de bbox. El ETL lo cuenta diario con la misma caché.
- **Anti doble conteo**: el sistema detecta si el lugar ya cae dentro del bbox de su ciudad y avisa antes de atribuirlo.
- **Alcance**: esta función es posterior al frontend; hoy el catálogo se edita como datos en `famous_sites.py`.

## Fase 4 — Backend hexagonal
- **Objetivo**: API de KPIs y ciudades.
- **Entregables**: FastAPI + Mangum con endpoints, dominio con Tourism Score (fórmula), tests con pytest.
- **Mejores prácticas**: puertos/adaptadores (dominio sin dependencias), Pydantic para contratos, OpenAPI autodocumentado.

## Fase 5 — Frontend
- **Objetivo**: dashboard ejecutivo + mapa.
- **Entregables**: React + Vite con KPIs, gráficos ECharts, mapa Leaflet, login.
- **Mejores prácticas**: componentes pequeños, TanStack Query para caché, tipos compartidos con el backend.

## Fase 6 — Data Quality Engine
- **Objetivo**: medir y alertar la calidad de datos.
- **Entregables**: Lambda post-ETL, tabla de métricas en PostgreSQL, alarmas CloudWatch.
- **Mejores prácticas**: umbrales accionables, alertar solo lo crítico (no notificar todo).

## Fase 7 — Tourism Score y ML
- **Objetivo**: score con pesos + clustering.
- **Entregables**: fórmula en el dominio, notebook de clustering, artefactos en S3.
- **Mejores prácticas**: empezar con regla simple y medir; ML solo con datos acumulados; reproducibilidad (semilla fija).

## Fase 8 — AI Assistant
- **Objetivo**: consultas en lenguaje natural.
- **Entregables**: chat con Groq, text-to-SQL sobre vistas pre-agregadas.
- **Mejores prácticas**: validar el SQL generado (solo lectura), restringir a vistas whitelist, citar fuentes para evitar alucinaciones.

---

# Decisiones Pendientes

- **Autenticación** del dashboard: Cognito vs API key.
- **RDS vs Aurora Serverless v2**: Aurora escala solo pero es más costoso; RDS t3.micro alcanza para el MVP.
- **Procesamiento incremental**: esquema de `last_sync` por fuente.
- **Tourism Score**: empezar como fórmula con pesos y validar el ML después.

---

# Roadmap Futuro

- Escalar de Perú a Sudamérica (REST Countries cobra relevancia)
- Integración con Booking
- Integración con Skyscanner
- Integración con Google Places
- Predicción avanzada
- Reportes automáticos PDF
- Agentes IA especializados
- Recomendaciones inteligentes
- **Alta manual de sitios turísticos desde el panel de Admin**: catálogo de sitios famosos en archivo YAML/JSON (editable sin tocar código), búsqueda en OSM por nombre desde el panel, atribución de ciudad con detección de doble conteo. Ver sección de Fase 3.

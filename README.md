# Plataforma de Product Analytics en AWS

Proyecto de portafolio para un rol de **Senior Data Engineer**. Toma eventos de uso de un producto,
los limpia, los guarda en un data lake y responde preguntas de producto con SQL:
*¿dónde abandonan los usuarios? ¿cuántos vuelven? ¿qué plataforma convierte mejor?*

> Los datos son **sintéticos** (los genera `src/generate_events.py`). Los números de este documento
> salen de correr el proyecto con la semilla fija `42`, no de un producto real.

## 1. Qué problema resuelve

Un equipo de producto necesita métricas confiables (funnel, retención, DAU/MAU), pero los eventos
llegan sucios (duplicados, campos nulos) y cada análisis se hace a mano. Este proyecto construye el
camino completo: **evento crudo → dato validado → métrica en SQL**, repetible y con tests.

## 2. Arquitectura

```
App web/mobile        S3 raw             ETL (Python)            S3 curated             Athena (SQL)
 eventos JSON  ───►  events.jsonl  ───►  validar + deduplicar ──►  Parquet por fecha ──►  funnel, retención,
                                          └─► data/rejected         (event_date=...)       DAU/MAU, conversión
```

| Capa | Local (para probarlo sin cuenta AWS) | En AWS |
|---|---|---|
| Almacenamiento | carpeta `data/` | **S3** (bucket cifrado, sin acceso público) |
| ETL | `src/etl.py` (pandas + pyarrow) | mismo código, pensado para ejecutarse en Glue Python Shell o Lambda |
| Catálogo | n/a | **Glue Data Catalog** (`aws/template.yaml`) |
| Consultas SQL | **DuckDB** sobre el Parquet | **Athena** sobre el mismo Parquet |
| Infra | n/a | **CloudFormation** (`aws/template.yaml`) |

La idea clave: **el mismo Parquet y las mismas queries SQL** corren en local y en Athena. Eso permite
desarrollar y testear rápido sin pagar nada, y luego desplegar igual.

## 3. Cómo correrlo

```bash
pip install -r requirements.txt
cd src && python run_pipeline.py     # genera datos, ETL, corre el SQL, guarda results/*.csv
cd .. && pytest -q tests              # tests de calidad de datos
```

Probado con Python 3.13 y 3.14 en Windows.

## 4. Qué hace cada pieza

**`src/generate_events.py`** simula 5.000 usuarios recorriendo un funnel
(`signup → onboarding_complete → feature_used → add_to_cart → purchase`) más visitas posteriores
(`session_start`). Inyecta ~1% de duplicados y ~0,5% de filas sin `user_id` para que el ETL tenga
trabajo real.

**`src/etl.py`** aplica 4 reglas de calidad (claves no nulas, evento en catálogo, timestamp válido,
sin duplicados por `event_id`), escribe **Parquet particionado por `event_date`** y guarda lo
rechazado en `data/rejected/` en vez de borrarlo en silencio. Es idempotente: correrlo dos veces no
duplica datos. En la corrida de referencia: 21.583 filas crudas → 106 rechazadas, 213 duplicados,
21.264 curadas.

**`sql/`** contiene las métricas de producto:

| Archivo | Métrica | Técnica SQL |
|---|---|---|
| `01_funnel.sql` | Conversión paso a paso | `FILTER`, `UNION ALL`, `LAG`, `FIRST_VALUE` |
| `02_retention.sql` | Retención D1/D7/D14/D30 por cohorte semanal | CTEs, self-join, `DATE_DIFF` |
| `03_dau_mau.sql` | DAU, MAU móvil de 30 días, stickiness | ventana móvil con join por rango de fechas |
| `04_conversion_by_platform.sql` | Compra por web/iOS/Android | agregación por segmento |

**`tests/test_quality.py`** verifica sobre la capa curada: sin nulos en claves, `event_id` único,
eventos dentro del catálogo y funnel monótono decreciente.

**`aws/template.yaml`** crea bucket S3, base y tabla en Glue y un workgroup de Athena. Decisiones:
- *Partition projection*: Athena calcula las particiones por fecha, sin crawlers ni `MSCK REPAIR`.
- *Tope de 10 GB escaneados por query*: control de costos.
- *Parquet + particiones por fecha*: Athena cobra por datos escaneados, así que se lee menos.
- *Bucket cifrado, sin acceso público, con expiración de resultados a 14 días*.

**`aws/deploy_and_query.py`** sube el Parquet a S3 y ejecuta las queries en Athena con boto3.

## 5. Resultados de la corrida de referencia (datos sintéticos)

- **Funnel:** signup 5.000 → onboarding 69,6% → feature 79,0% del paso anterior → carrito 52,3% →
  compra 41,1%. Compra total: **11,8%** de los registrados. La mayor pérdida en
  usuarios está en el onboarding (1.521 usuarios, 30,4%), y el paso con peor conversión es
  *add_to_cart* → *purchase* (41,1%).
- **Retención:** D1 ≈ 41–47%, D7 ≈ 31–35%, D30 ≈ 23–26%.
- **Conversión por plataforma:** Android 13,3%, iOS 12,3%, web 10,9%.
- **Nota sobre DAU/MAU:** en datos sintéticos los registros terminan al día 30, por eso el DAU cae
  hacia el final. Con tráfico real esa curva sería distinta.

## 6. Qué probé y qué no

- Probado: generación, ETL, las 4 queries (en DuckDB) y los 4 tests.
- **No probado contra una cuenta AWS real:** `template.yaml` y `deploy_and_query.py` están escritos
  siguiendo la documentación, pero conviene desplegarlos y validarlos antes de afirmar que corren
  tal cual. Las queries usan sintaxis común a DuckDB y Athena (Trino), pero podrían necesitar
  ajustes menores.

## 7. Cómo evolucionaría en producción

1. **Ingesta en streaming** con Kinesis Data Firehose → S3 (hoy el input es un archivo).
2. **Orquestación** con Airflow (MWAA) o Step Functions, con reintentos y alertas.
3. **Transformaciones versionadas con dbt** y capas bronze/silver/gold.
4. **Calidad con Great Expectations o dbt tests** y alertas si falla una regla.
5. **CI/CD** con GitHub Actions: tests + `cfn-lint` en cada PR.
6. **Gobierno:** permisos con Lake Formation, enmascarado de datos personales.
7. **Filtrar por `event_date` en las queries:** las consultas de demo leen todo el rango; en producción
   filtrarían por fecha (por ejemplo, los últimos 30 días) para que Athena lea solo esas particiones
   y el costo no crezca con el histórico.


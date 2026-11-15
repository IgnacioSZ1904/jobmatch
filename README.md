# 🎯 JobMatch

Aplicación local que **recoge ofertas de empleo de software** de varias plataformas, las
normaliza, las guarda en SQLite y las **puntúa según tu perfil** (reglas con pesos + similitud
semántica con embeddings). Cada oferta muestra el **desglose de por qué** tiene esa puntuación.

> Proyecto personal y de portfolio. Todo corre en local y es gratuito.

## Funcionalidades (MVP, fase 1)

- **Cuestionario de perfil** por pasos (roles, nivel, tecnologías, modalidad, salario, idiomas,
  exclusiones y un resumen libre), guardado en `data/profile.yaml`.
- **Importación desde LinkedIn**: sube el PDF de tu perfil (*Más → Guardar en PDF*) y se
  prerrellenan tecnologías, años de experiencia, puesto, ubicación, idiomas y resumen.
- **Escala de niveles 1–5** explicada (Básico, Principiante, Autónomo, Avanzado, Experto).
- **Fuentes**: Remotive, Arbeitnow y RemoteOK (APIs públicas, sin credenciales) e InfoJobs
  (API oficial; requiere registrar una app gratuita en developer.infojobs.net y poner
  `INFOJOBS_CLIENT_ID` e `INFOJOBS_CLIENT_SECRET` en `.env`).
- **Otros portales** (LinkedIn, InfoJobs web, Indeed, Tecnoempleo): enlaces de búsqueda generados
  con tu perfil y **importación manual** de ofertas (URL + texto) para puntuarlas igual.
- **Nivel "Prácticas"** en el perfil y detección de ofertas de prácticas o beca; al puntuar,
  prácticas y junior cuentan como el mismo nivel.
- **Normalización**: tecnologías con taxonomía y alias, seniority y años, salario a EUR/año,
  modalidad (remoto/híbrido/presencial), alcance del remoto, país e idiomas.
- **Deduplicación** dentro de cada fuente y entre fuentes (empresa + título, `rapidfuzz`).
- **Scoring 0–100**: filtros duros, componentes ponderados y penalizaciones:

  | Componente | Peso |
  |---|---|
  | Skills (nivel, imprescindibles, carencias, "quiero aprender") | 35 |
  | Semántico (embeddings perfil ↔ oferta) | 25 |
  | Seniority | 15 |
  | Modalidad / ubicación | 10 |
  | Salario (neutro si no se publica) | 10 |
  | Idioma | 5 |

- **Interfaz Streamlit**: inicio con "Actualizar ofertas", ranking con filtros, pestaña de
  ofertas filtradas, estados (nueva, vista, interesante, descartada, aplicada) y notas.

## Arquitectura

```
app/ (Streamlit)  ──►  jobmatch.services  ──►  connectors → normalize → dedup → storage → scoring
                                                                    (SQLite)    (reglas + embeddings)
```

`app/` no contiene lógica de negocio: todo pasa por `jobmatch.services`, de modo que una API
FastAPI podrá reutilizarlo sin cambios.

```
src/jobmatch/
├── config.py            # rutas, pesos, tipos de cambio
├── models.py            # JobOffer, OfferState, OfferScore (SQLModel)
├── profile/             # modelo, cuestionario declarativo, YAML
├── connectors/          # una clase por fuente (interfaz Connector)
├── normalize/           # skills, seniority, salario, ubicación, idiomas
├── dedup.py
├── storage.py           # repositorio sobre SQLite
├── scoring/             # reglas, embeddings y combinación
└── services.py          # casos de uso: refresh_offers, list_offers, set_status…
```

## Puesta en marcha

Requiere Python 3.11+.

```bash
uv venv && uv pip install -e ".[dev]"          # o: python -m venv .venv && pip install -e ".[dev]"
uv pip install -e ".[semantic]"                # opcional: embeddings reales (~120 MB + PyTorch)
streamlit run app/Home.py
```

Sin el extra `semantic` se usa un embedder ligero de bolsa de palabras como respaldo.
Con él, se usa `paraphrase-multilingual-MiniLM-L12-v2` (ES/EN, CPU).

## Tests

```bash
pytest          # sin red: los conectores se prueban con respuestas grabadas en tests/fixtures
ruff check .
```

## Roadmap

- **Fase 1 (resto)**: Adzuna (España) y página de análisis de mercado.
- **Fase 2**: We Work Remotely, explicación opcional con LLM, exportar a CSV/Excel, pesos
  ajustables desde la UI.
- **Fase 3**: API FastAPI + frontend React.

## Uso responsable

Solo se usan APIs públicas, con `User-Agent` identificable y atribución a cada fuente
(RemoteOK la exige). No se hace scraping de LinkedIn ni de Indeed.

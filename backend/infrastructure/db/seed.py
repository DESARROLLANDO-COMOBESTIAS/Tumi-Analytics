"""Seed idempotente del Dataset Perú: capitales de departamento.

Ejecutar repetidas veces no duplica datos (ON CONFLICT DO NOTHING).
"""

from sqlalchemy.dialects.postgresql import insert

from infrastructure.db.models import City, PoiCategory
from infrastructure.db.session import SessionLocal

CITIES: list[tuple[str, str, float, float, int]] = [
    ("Lima", "Lima", -12.0464, -77.0428, 8894000),
    ("Callao", "Callao", -12.0666, -77.1512, 567000),
    ("Arequipa", "Arequipa", -16.4090, -71.5375, 860000),
    ("Cusco", "Cusco", -13.5319, -71.9675, 437000),
    ("Trujillo", "La Libertad", -8.1159, -79.0289, 919000),
    ("Chiclayo", "Lambayeque", -6.7714, -79.8409, 552000),
    ("Piura", "Piura", -5.1945, -80.6328, 474000),
    ("Iquitos", "Loreto", -3.7433, -73.2517, 377000),
    ("Pucallpa", "Ucayali", -8.3816, -74.5742, 326000),
    ("Huancayo", "Junín", -12.0651, -75.2049, 456000),
    ("Cajamarca", "Cajamarca", -7.1617, -78.5127, 246000),
    ("Tacna", "Tacna", -18.0146, -70.2533, 296000),
    ("Ica", "Ica", -14.0678, -75.7286, 296000),
    ("Ayacucho", "Ayacucho", -13.1588, -74.2232, 216000),
    ("Puno", "Puno", -15.8402, -70.0219, 128000),
    ("Huaraz", "Áncash", -9.5278, -77.5281, 121000),
    ("Chachapoyas", "Amazonas", -6.2314, -77.8745, 28000),
    ("Huánuco", "Huánuco", -9.9306, -76.2422, 196000),
    ("Cerro de Pasco", "Pasco", -10.6856, -76.2628, 58000),
    ("Tumbes", "Tumbes", -3.5669, -80.4516, 96000),
    ("Moyobamba", "San Martín", -6.0347, -76.9727, 50000),
    ("Abancay", "Apurímac", -13.6336, -72.8820, 58000),
    ("Moquegua", "Moquegua", -17.1950, -70.9350, 69000),
    ("Puerto Maldonado", "Madre de Dios", -12.5933, -69.1893, 85000),
    ("Huancavelica", "Huancavelica", -12.7863, -74.9764, 49000),
]


POI_CATEGORIES: list[tuple[str, str]] = [
    ("hoteles", "Hoteles y alojamientos"),
    ("restaurantes", "Restaurantes y bares"),
    ("museos", "Museos"),
    ("galerias", "Galerías de arte"),
    ("arte_urbano", "Arte y esculturas"),
    ("parques", "Parques y jardines"),
    ("reservas", "Reservas naturales"),
    ("hospitales", "Hospitales"),
    ("atracciones", "Atracciones turísticas"),
    ("arqueologicos", "Sitios arqueológicos y ruinas"),
    ("castillos", "Castillos y fortalezas"),
    ("murallas", "Murallas y portadas históricas"),
    ("monumentos", "Monumentos y memoriales"),
    ("iglesias", "Iglesias y monasterios"),
    ("miradores", "Miradores"),
    ("playas", "Playas"),
    ("montanas", "Montañas y picos"),
    ("cuevas", "Cuevas y cavernas"),
    ("volcanes", "Volcanes"),
    ("aguas_termales", "Aguas termales y manantiales"),
    ("sin_clasificar", "Sin clasificar (revisar)"),
]


def run() -> None:
    with SessionLocal() as session:
        statement = insert(City).values(
            [
                {
                    "name": name,
                    "department": department,
                    "latitude": latitude,
                    "longitude": longitude,
                    "population": population,
                }
                for name, department, latitude, longitude, population in CITIES
            ]
        ).on_conflict_do_nothing(index_elements=["name"])
        session.execute(statement)

        category_statement = insert(PoiCategory).values(
            [
                {"code": code, "name": name}
                for code, name in POI_CATEGORIES
            ]
        ).on_conflict_do_nothing(index_elements=["code"])
        session.execute(category_statement)
        session.commit()
    print(
        f"Seed completado: {len(CITIES)} capitales y {len(POI_CATEGORIES)} categorías de POIs."
    )


if __name__ == "__main__":
    run()

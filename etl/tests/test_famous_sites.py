from etl.sources.famous_sites import FAMOUS_SITES

SEED_CITIES = {
    "Lima", "Callao", "Arequipa", "Cusco", "Trujillo", "Chiclayo", "Piura",
    "Iquitos", "Pucallpa", "Huancayo", "Cajamarca", "Tacna", "Ica", "Ayacucho",
    "Puno", "Huaraz", "Chachapoyas", "Huánuco", "Cerro de Pasco", "Tumbes",
    "Moyobamba", "Abancay", "Moquegua", "Puerto Maldonado", "Huancavelica",
}

REQUIRED = ("name", "city", "latitude", "longitude", "radius_deg")


class TestFamousSites:
    def test_cada_sitio_tiene_campos_obligatorios(self):
        for site in FAMOUS_SITES:
            for field in REQUIRED:
                assert field in site, site

    def test_nombres_unicos(self):
        names = [site["name"] for site in FAMOUS_SITES]
        assert len(names) == len(set(names))

    def test_coordenadas_validas_peru(self):
        for site in FAMOUS_SITES:
            assert -19.0 <= site["latitude"] <= 0.0, site
            assert -82.0 <= site["longitude"] <= -68.0, site
            assert site["radius_deg"] > 0, site

    def test_ciudad_de_atribucion_en_catalogo(self):
        for site in FAMOUS_SITES:
            assert site["city"] in SEED_CITIES, site

    def test_hay_sitios_famosos_curados(self):
        assert len(FAMOUS_SITES) >= 5

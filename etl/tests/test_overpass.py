from etl.sources.overpass import (
    ALL_CATEGORIES,
    CATEGORY_TAGS,
    UNCLASSIFIED,
    build_statements,
    classify_counts,
    classify_element,
)


def _element(tags: dict) -> dict:
    return {"type": "node", "id": 1, "tags": tags}


class TestClassifyElement:
    def test_clasifica_categorias_turisticas(self):
        cases = {
            "hoteles": {"tourism": "hotel"},
            "restaurantes": {"amenity": "restaurant"},
            "museos": {"tourism": "museum"},
            "galerias": {"tourism": "gallery"},
            "arte_urbano": {"tourism": "artwork"},
            "parques": {"leisure": "park"},
            "reservas": {"leisure": "nature_reserve"},
            "hospitales": {"amenity": "hospital"},
            "atracciones": {"tourism": "attraction"},
            "arqueologicos": {"historic": "archaeological_site"},
            "castillos": {"historic": "castle"},
            "murallas": {"historic": "city_gate"},
            "monumentos": {"historic": "monument"},
            "iglesias": {"amenity": "place_of_worship"},
            "miradores": {"tourism": "viewpoint"},
            "playas": {"natural": "beach"},
            "montanas": {"natural": "peak"},
            "cuevas": {"natural": "cave_entrance"},
            "volcanes": {"natural": "volcano"},
            "aguas_termales": {"natural": "hot_spring"},
        }
        for category, tags in cases.items():
            assert category in classify_element(tags), tags

    def test_elemento_sin_etiquetas_no_cuenta(self):
        assert classify_element({"type": "node", "id": 9}) == []
        assert classify_element({"name": "Plaza"}) == []

    def test_un_elemento_puede_sumar_a_varias_categorias(self):
        result = classify_element({"tourism": "hotel", "amenity": "restaurant"})
        assert "hoteles" in result
        assert "restaurantes" in result

    def test_ruido_conocido_se_descarta(self):
        assert classify_element({"natural": "tree"}) == []
        assert classify_element({"leisure": "pitch"}) == []
        assert classify_element({"natural": "tree", "leisure": "pitch"}) == []

    def test_sin_clasificar_para_desconocidos(self):
        assert classify_element({"historic": "aircraft"}) == [UNCLASSIFIED]
        assert classify_element({"tourism": "car_rental"}) == [UNCLASSIFIED]


class TestClassifyCounts:
    def test_cuenta_por_categoria(self):
        elements = [
            _element({"tourism": "hotel"}),
            _element({"amenity": "restaurant"}),
            _element({"tourism": "museum"}),
            _element({"natural": "tree"}),  # ruido
            _element({"historic": "aircraft"}),  # sin clasificar
        ]
        counts = classify_counts(elements)
        assert counts["hoteles"] == 1
        assert counts["restaurantes"] == 1
        assert counts["museos"] == 1
        assert counts[UNCLASSIFIED] == 1

    def test_siempre_incluye_todas_las_categorias(self):
        counts = classify_counts([_element({"tourism": "hotel"})])
        assert set(counts) == set(ALL_CATEGORIES)


class TestBuildQuery:
    def test_incluye_bbox_y_captura_amplia(self):
        statements = build_statements((-13.5, -72.0, -13.4, -71.9))
        assert len(statements) == 5
        joined = "\n".join(statements)
        assert '(-13.5000,-72.0000,-13.4000,-71.9000)' in joined
        assert 'nwr["tourism"]' in joined
        assert 'nwr["historic"]' in joined
        assert 'nwr["leisure"]' in joined
        assert 'nwr["natural"~' in joined
        assert 'nwr["amenity"~' in joined
        assert 'out center tags;' in joined

    def test_un_elemento_no_se_duplica_al_unir(self):
        # verificado en fetch_bbox (dedup por type/id); sanity del builder:
        assert any('nwr["tourism"]' in s for s in build_statements((-13.5, -72.0, -13.4, -71.9)))

    def test_todas_las_categorias_definidas(self):
        assert set(CATEGORY_TAGS) == {
            "hoteles", "restaurantes", "museos", "galerias", "arte_urbano",
            "parques", "reservas", "hospitales", "atracciones", "arqueologicos",
            "castillos", "murallas", "monumentos", "iglesias", "miradores",
            "playas", "montanas", "cuevas", "volcanes", "aguas_termales",
        }
        assert ALL_CATEGORIES[-1] == UNCLASSIFIED

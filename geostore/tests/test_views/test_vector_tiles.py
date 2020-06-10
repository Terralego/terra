import json
from time import sleep
from urllib.parse import unquote

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from rest_framework.test import APITestCase

from geostore import GeometryTypes
from geostore.models import Layer, LayerGroup, LayerExtraGeom
from geostore.settings import app_settings
from geostore.tests.factories import LayerFactory
from geostore.tests.utils import get_files_tests
from geostore.tiles.helpers import VectorTile, guess_maxzoom, guess_minzoom


@override_settings(CACHES={
    'default': {
        'BACKEND': ('django.core.cache.backends'
                    '.locmem.LocMemCache')
    }})
class VectorTilesNoLayerTestCase(APITestCase):
    group_slug = 'mygroup'

    def test_group_tilejson_fail_no_layer(self):
        response = self.client.get(
            reverse('group-tilejson', args=[self.group_slug]),
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_404_NOT_FOUND, response.status_code)

    def test_vector_tiles_view_without_layer(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('group-tiles', args=[self.group_slug, 10, 515, 373]))
        self.assertEqual(HTTP_404_NOT_FOUND, response.status_code)


class VectorTilesTestCase(TestCase):
    group_name = 'mygroup'

    def setUp(self):
        layer_settings = {'metadata': {'attribution': 'plop'}}

        self.layer = LayerFactory(name="layerLine", settings=layer_settings)
        self.layer_extra_geom = LayerExtraGeom.objects.create(layer=self.layer,
                                                              geom_type=GeometryTypes.LineString,
                                                              title='Extra geometry')
        self.mygroup = LayerGroup.objects.create(name='mygroup', slug='mygroup')
        self.mygroup.layers.add(self.layer)

        self.layer.from_geojson(
            geojson_data='''
            {
            "type": "FeatureCollection",
            "features": [
                {
                "type": "Feature",
                "properties": {
                    "foo": "bar",
                    "baba": "fifi"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                    [
                        1.3700294494628906,
                        43.603640347220924
                    ],
                    [
                        1.2984466552734375,
                        43.57902295875415
                    ]
                    ]
                }
                }
            ]
            }
        ''')

        self.layerPoint = LayerFactory(name="layerPoint", settings=layer_settings)
        self.yourgroup = LayerGroup.objects.create(name='yourgroup', slug='yourgroup')
        self.yourgroup.layers.add(self.layerPoint)

        self.layerPoint.from_geojson(

            geojson_data='''
            {
            "type": "FeatureCollection",
            "features": [
                {
                "type": "Feature",
                "properties": {
                    "foo": "bar"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        1.3700294494628906,
                        43.603640347220924
                    ]
                }
                }
            ]
            }
        ''')

    def test_group_tilejson(self):
        response = self.client.get(
            reverse('group-tilejson', args=[self.mygroup.slug]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost'
        )
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tile_json = response.json()

        self.assertTrue(tile_json['attribution'])
        self.assertTrue(tile_json['description'] is None)
        self.assertGreater(len(tile_json['vector_layers']), 0)
        self.assertGreater(len(tile_json['vector_layers'][0]['fields']), 0)
        unquoted_reverse = unquote(reverse('group-tiles-pattern', args=[self.mygroup.slug]))
        self.assertEqual(
            tile_json['tiles'][0],
            f"http://localhost{unquoted_reverse}"
        )

    def test_layer_tilejson(self):
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = response.json()
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)
        unquoted_reverse = unquote(reverse('layer-tiles-pattern', args=[self.layer.pk]))
        self.assertEqual(
            tilejson['tiles'][0],
            f"http://localhost{unquoted_reverse}"
        )

    @override_settings(TERRA_TILES_HOSTNAMES=['http://a.tiles.local',
                                              'http://b.tiles.local',
                                              'http://c.tiles.local'])
    def test_layer_tilejson_with_custom_hostnames(self):
        sleep(1)
        unquoted_reverse = unquote(reverse('layer-tiles-pattern', args=[self.layer.pk]))
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk])
        )
        self.assertEqual(HTTP_200_OK, response.status_code)
        tilejson = response.json()
        self.assertListEqual(
            tilejson['tiles'],
            [f"{host}{unquoted_reverse}" for host in ['http://a.tiles.local',
                                                      'http://b.tiles.local',
                                                      'http://c.tiles.local']]
        )

    def test_layer_tilejson_without_features(self):
        self.layer.features.all().delete()
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = response.json()
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)

    def test_404_tile_pattern(self):
        response = self.client.get(
            reverse(
                'layer-tiles-pattern',
                kwargs={'pk': self.layer.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vector_group_tiles_view(self):
        # first query that generate the cache
        with self.assertNumQueries(9):
            # verify data is cached
            response = self.client.get(
                reverse(
                    'group-tiles',
                    kwargs={'slug': self.mygroup.slug, 'z': 10, 'x': 515, 'y': 373})
            )
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        original_content = response.content

        with self.assertNumQueries(6):
            # verify data is cached
            response = self.client.get(
                reverse(
                    'group-tiles',
                    kwargs={'slug': self.mygroup.slug, 'z': 10, 'x': 515, 'y': 373})
            )

        self.assertEqual(
            original_content,
            response.content
        )

        response = self.client.get(
            reverse('group-tiles', args=[self.group_name, 10, 1, 1]))

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertFalse(len(response.content))

    def test_vector_layer_tiles_view(self):
        # first query that generate the cache
        with self.assertNumQueries(10):
            response = self.client.get(
                reverse(
                    'layer-tiles',
                    kwargs={'pk': self.layer.pk, 'z': 10, 'x': 515, 'y': 373})
            )
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        with self.assertNumQueries(7):
            # verify data is cached
            response = self.client.get(
                reverse(
                    'layer-tiles',
                    kwargs={'pk': self.layer.pk, 'z': 10, 'x': 515, 'y': 373})
            )

        response = self.client.get(
            reverse('layer-tiles', kwargs={'pk': self.layer.pk, 'z': 10, 'x': 1, 'y': 1}))

        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(b'', response.content)

    @override_settings(MAX_TILE_ZOOM=9)
    def test_vector_group_tiles_view_max_tile_zoom_lower_actual_zoom(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('group-tiles', args=[self.mygroup.slug, 10, 515, 373]))
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(len(response.content), 113)

    @override_settings(MAX_TILE_ZOOM=9)
    def test_vector_layer_tiles_view_max_tile_zoom_lower_actual_zoom(self):
        # first query that generate the cache
        response = self.client.get(
            reverse('layer-tiles', args=[self.layer.pk, 10, 515, 373]))
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertEqual(len(response.content), 113)

    def test_filtering(self):
        tile = VectorTile(self.layer, "CACHINGCACHE")
        x, y, z = 16506, 11966, 15

        tile = tile.get_tile(
            x, y, z
        )
        self.assertGreater(len(tile), 0)

    def test_guess_maxzoom(self):
        # guess_maxzoom returning -1 when TypeError is raised14)
        self.assertEqual(
            guess_maxzoom(self.layerPoint),
            14)

        self.assertEqual(
            guess_maxzoom(self.layer) is not None,
            True)

        # test guess_maxzoom returns sensible value from OSM Fontainebleau paths&tracks
        chunk_fontainebleau_geojson = get_files_tests('chunk_fontainebleau.geojson')

        call_command(
            'import_geojson', chunk_fontainebleau_geojson,
            '-gr', 'maxzoom_test',
            '-ln', 'chunk_fontainebleau',
            verbosity=0)

        layer_chunk_fontainebleau = Layer.objects.get(name='chunk_fontainebleau')

        self.assertEqual(guess_maxzoom(layer_chunk_fontainebleau), 13)

    def test_guess_minzoom(self):
        self.assertEqual(
            guess_minzoom(self.layerPoint),
            0)

        self.assertTrue(isinstance(
            guess_minzoom(self.layer),
            int)
        )


class VectorTilesSpecialTestCase(TestCase):
    group_name = 'mygroup'

    def setUp(self):
        # Same as default with properties filter not None
        settings = {'metadata': {'attribution': 'plop'}, 'tiles': {
            'minzoom': 0,
            'maxzoom': 22,
            'pixel_buffer': 4,
            'features_filter': None,  # Json
            'properties_filter': 'Test',  # Array of string
            'features_limit': 10000,
        }}

        self.layer = LayerFactory(name="layerLine", settings=settings)
        self.group = LayerGroup.objects.create(name='mygroup', slug='mygroup')
        self.group.layers.add(self.layer)

        self.geojson_data = '''
            {
            "type": "FeatureCollection",
            "features": [
                {
                "type": "Feature",
                "properties": {
                    "foo": "bar",
                    "baba": "fifi"
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                    [
                        1.3700294494628906,
                        43.603640347220924
                    ],
                    [
                        1.2984466552734375,
                        43.57902295875415
                    ]
                    ]
                }
                }
            ]
            }
        '''
        self.layer.from_geojson(geojson_data=self.geojson_data)

    def test_group_tilejson_with_properties(self):
        response = self.client.get(
            reverse('group-tilejson', args=[self.group_name]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = response.json()
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)

    def test_layer_tilejson_with_properties(self):
        response = self.client.get(
            reverse('layer-tilejson', args=[self.layer.pk]),
            # HTTP_HOST required to build the tilejson descriptor
            HTTP_HOST='localhost')
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertGreater(len(response.content), 0)

        tilejson = json.loads(response.content)
        self.assertTrue(tilejson['attribution'])
        self.assertTrue(tilejson['description'] is None)
        self.assertGreater(len(tilejson['vector_layers']), 0)
        self.assertGreater(len(tilejson['vector_layers'][0]['fields']), 0)

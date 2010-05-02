from datetime import date
import logging

from django.test import TestCase

from library.models import *

class Tests(TestCase):

    def setUp(self):
        self.logger = logging.getLogger()

    def test_views_missing(self):
        from api.views import *
        from django.http import Http404
        try:
            missing(None, 1).status_code
            raise Exception('should have thrown Http404')
        except Http404:
            print 'expected result'
            
        from library.models import *
        Library.objects.create(pk=1, name='foo')

        self.assertEqual('{"processing": 2, "data": {}}', missing(None, 1).content)

    def test_release_group_no_releases(self):
        '''
        http://github.com/aroscoe/music-inbox/issues#issue/1
        tests release groups that don't have any releases
        '''
        from library.models import *
        from musicbrainz2.webservice import *
        artist = MBArtist.objects.create(name = 'Galactic', mb_id = 'http://musicbrainz.org/artist/cabbdf87-5cb2-4f3c-be65-254655c87508.html')
        self.assertEquals((None, None),
                          artist.get_release_date('http://musicbrainz.org/release-group/32195cf1-5d5c-412e-b308-1d586c08e6c4.html', logger))

        
    def test_null_release_dates(self):
        '''
        makes sure the Library._newest_ function can accept null MBAlbum.release_date's
        '''
        
        from datetime import datetime
        import sys
        
        artist = MBArtist.objects.create(name = 'foo', mb_id = 'http://bar.baz')
        # null release dates
        album1 = MBAlbum.objects.create(name = 'bar', mb_id = 'http://bar.com/album1', artist = artist)
        album2 = MBAlbum.objects.create(name = 'bar', mb_id = 'http://bar.com/album2', artist = artist)

        # non-null release date
        album3 = MBAlbum.objects.create(name = 'bar', mb_id = 'http://bar.com/album3', artist = artist, release_date = datetime.now())
        
        library = Library.objects.create(pk = 1, name = 'foo')

        self.assertEquals(-sys.maxint, library._newest_(album1, album2))
        self.assertEquals(sys.maxint, library._newest_(album1, album3))
        self.assertEquals(-sys.maxint, library._newest_(album3, album2))


    def test_fetch_albums(self):
        artist = MBArtist.objects.create(name='4 Non Blondes',
                                         mb_id='http://musicbrainz.org/artist/efef848b-63e4-4323-8ef7-69a48fbdd51d')
        artist.fetch_albums(logger)
        self.assertEquals(1, len(MBAlbum.objects.all()))
        album = MBAlbum.objects.get(name='Bigger, Better, Faster, More!')
        self.assertNotEquals(None, album)
        self.assertEquals('http://musicbrainz.org/release-group/0d26ee11-05f3-3a02-ba40-1414fa325554',
                          album.mb_id)
        self.assertEquals(date(1992, 10, 13), album.release_date)
        self.assertEquals(artist, album.artist)


    def test_get_release_date(self):
        artist = MBArtist.objects.create(name='4 Non Blondes',
                                         mb_id='http://musicbrainz.org/artist/efef848b-63e4-4323-8ef7-69a48fbdd51d')
        release_date, asin = artist.get_release_date('http://musicbrainz.org/release-group/0d26ee11-05f3-3a02-ba40-1414fa325554', logger)
        self.assertEquals(date(1992, 10, 13), release_date)
        
        
    def test_lookup_artist_for_new_artist(self):
        library = Library.objects.create(name='test')
        artist = library.artist_set.create(name='4 Non Blondes')
        
        lookup_artist(artist, self.logger)
        
        self.assertEquals('http://musicbrainz.org/artist/efef848b-63e4-4323-8ef7-69a48fbdd51d', artist.mb_artist_id)
        
        mb_artist = MBArtist.objects.get(name='4 Non Blondes')
        self.assertNotEquals(None, mb_artist)
        self.assertEquals('http://musicbrainz.org/artist/efef848b-63e4-4323-8ef7-69a48fbdd51d',
                          mb_artist.mb_id)
        
        self.assertEquals(1, len(MBAlbum.objects.all()))
        album = MBAlbum.objects.get(name='Bigger, Better, Faster, More!')
        self.assertNotEquals(None, album)
        self.assertEquals('http://musicbrainz.org/release-group/0d26ee11-05f3-3a02-ba40-1414fa325554',
                          album.mb_id)
        self.assertEquals(date(1992, 10, 13), album.release_date)
        self.assertEquals(mb_artist, album.artist)
        
    def test_lookup_artist_for_existing_artist(self):
        mb_artist = MBArtist.objects.create(name='4 Non Blondes',
                                            mb_id='http://musicbrainz.org/artist/efef848b-63e4-4323-8ef7-69a48fbdd51d')
        library = Library.objects.create(name='test')
        artist = library.artist_set.create(name='4 Non Blondes')

        lookup_artist(artist, self.logger)
        
        self.assertEquals(mb_artist.mb_id, artist.mb_artist_id)
        # albums should not be fetched
        self.assertEquals(0, len(MBAlbum.objects.all()))

    def test_lookup_artist_for_new_artist_fixes_name(self):
        library = Library.objects.create(name='test')
        artist = library.artist_set.create(name='4 non blondes')
        
        lookup_artist(artist, self.logger)
        
        self.assertEquals('4 Non Blondes', artist.name)

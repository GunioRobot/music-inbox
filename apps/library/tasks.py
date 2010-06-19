import logging
import plistlib
from datetime import timedelta

from django.conf import settings
from django.utils import simplejson

from celery.decorators import task, periodic_task

from library.models import *

@task
def import_form_data(library_id, form_data, **kwargs):
    '''Reads a file with json library data and imports it into the library'''
    logger = import_form_data.get_logger(**kwargs)
    library = Library.objects.get(pk=library_id)

    logger.info('processing form for library %s' % library)

    for artist, albums in form_data.lists():
        # skip library name key-value pair
        if artist == 'name':
            continue
        logger.debug('artist %s, albums %s' % (artist, albums))
        artist, created = library.artist_set.get_or_create(name=artist)
        for album in albums:
            artist.album_set.get_or_create(name=album)

    library.processing = False
    library.save()

    diff_albums.delay(library_id)

@task
def import_itunes_file(library_id, library_filename, **kwargs):
    '''Reads itunes xml file and extracs artists and albums from its tracks.
    
    Saves artist and tracks to database as part of the library.
    
    '''
    logger = import_itunes_file.get_logger(**kwargs)
    
    logger.info("reading file %s for library %s" 
                 % (library_filename, library_id))
    
    library = Library.objects.get(pk=library_id)
    
    itunes = plistlib.readPlist(library_filename)
    tracks = itunes["Tracks"]
    
    for track in tracks.values():
        if track.get("Artist") and track.get("Album"):
            artist, created = library.artist_set.get_or_create(name=track["Artist"])
            artist.album_set.get_or_create(name=track["Album"])
            if track.get("Play Count"):
                artist.play_count += track["Play Count"]
                artist.save()
    library.processing = False
    library.save()
    
    diff_albums.delay(library_id)

@task(routing_key='musicbrainz.diff_albums')
def diff_albums(library_id, **kwargs):
    ''' '''
    logger = diff_albums.get_logger(**kwargs)
    logger.debug("diffing albums of library %s" % library_id)
    
    library = Library.objects.get(pk=library_id)
    
    album_diff(library, logger)

@task(routing_key='musicbrainz.fetch_albums')
def fetch_albums(mb_artist_id, **kwargs):
    logger = fetch_albums.get_logger(**kwargs)
    artist = MBArtist.objects.get(mb_id=mb_artist_id)
    artist.fetch_albums(logger)

@periodic_task(run_every=timedelta(days=1))
def fetch_albums_cron(**kwargs):
    logger = fetch_albums_cron.get_logger(**kwargs)
    logger.info('running fetch albums cron job')
    for artist in MBArtist.objects.all():
        fetch_albums.delay(artist.mb_id, logger)

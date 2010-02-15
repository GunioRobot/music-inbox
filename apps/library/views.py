from django.http import Http404
from django.conf import settings
from django.views.generic.simple import direct_to_template
from library.models import Library as LibraryModel
from library.models import Artist
from library.forms import *
from library import signals
import threading

class LibraryView:
    def post_library(self, request):
        print "posted"
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            print "valid"
            library_name = form.cleaned_data['name']
            library_file = self._handle_uploaded_file(request.FILES['file'])
            
            # Create Library to send along with the signal and send pk back in the response
            library = LibraryModel(name=library_name)
            library.save()
            
            t = threading.Thread(target=signals.upload_done.send, kwargs={'sender': self, 'file': library_file, 'library': library})
            t.setDaemon(True)
            t.start()
            return library
        return None
    
    def _handle_uploaded_file(self, file):
        file_path = settings.UPLOADS_DIR + file.name
        destination = open(file_path, 'wb+')
        for chunk in file.chunks():
            destination.write(chunk)
        destination.close()
        return file_path

def upload(request):
    if request.method == 'POST':
        library = LibraryView().post_library(request)
        if library:
            return direct_to_template(request, 'library/success.html', locals())
    else:
        form = UploadFileForm()
    return direct_to_template(request, 'library/upload.html', locals())

def library(request, library_id): #TODO: remove duplication with read in apis
    artists = Artist.objects.filter(library=library_id).select_related()
    if artists:
        library = {}
        for artist in artists:
            library[artist.name] = artist.album_set.values_list('name', flat=True)
        return direct_to_template(request, 'library/library.html', locals())
    else:
        raise Http404

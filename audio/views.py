from django.shortcuts import render, redirect
from .forms import AudioFileForm

def upload_audio(request):
    if request.method == 'POST':
        form = AudioFileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('audio:upload_audio')
    else:
        form = AudioFileForm()
    return render(request, 'audio/upload_audio.html', {'form': form})

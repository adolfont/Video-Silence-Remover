import os
import shutil
import glob
from moviepy.editor import *
from pydub import AudioSegment
from pydub.utils import *
from tqdm import tqdm
import subprocess
from termcolor import colored

def install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])

def upgrade(package):
    subprocess.call(['pip', "install", "--upgrade", package])

def installModule(package):
    install(package)
    upgrade(package)

def fixImageMagickFolderInMoviePy():
    #search imagemagick exe
    magickExePath = []
    for root, dirs, files in os.walk("C:\\"):
        if "magick.exe" in files:
            magickExePath.append(os.path.join(root, "magick.exe"))
            break

    if not magickExePath:
        print(colored("Instale o ImageMagick para esse programa funcionar", "red"))
        exit()
    magickExePath = magickExePath[0]

    print(colored("Corrigindo MoviePy...", "green"))
    folderMoviePyConfigDefaults = os.path.dirname(sys.executable) + "/lib/site-packages/moviepy/"
    s = open(folderMoviePyConfigDefaults + "config_defaults.py").read()
    old = 'IMAGEMAGICK_BINARY = os.getenv(\'IMAGEMAGICK_BINARY\', \'auto-detect\')'
    new = 'IMAGEMAGICK_BINARY = r\"' + magickExePath + '\"'
    s = s.replace(old, new)
    f = open(folderMoviePyConfigDefaults + "config_defaults.py", 'w')
    f.write(s)
    f.close()

def initializeMoviePy():
    installModule("moviepy")

    fixImageMagickFolderInMoviePy()

def identifySilenceMomentsOfVideo(videoFilename, rmsOfSilence, timeOfSilenceInMilliseconds, mode = "DEBUG"):
    audioFile = AudioSegment.from_file(videoFilename, "mp4")
    videoFile = VideoFileClip(videoFilename)

    chunksOfAudio = make_chunks(audioFile, timeOfSilenceInMilliseconds)
    currentTime = 0.0
    startSilence = False
    fileCounter = 0

    silenceToRemoveTxt = open("silenceToRemove.txt", "w")
    if(mode == "DEBUG"):
        silenceFileTxt = open("log.txt", "w")
    it = 0
    listOfClipsToCombine = []
    print(colored("Buscando instantes de silêncio ao longo do vídeo...", "green"))
    for chunk in tqdm(chunksOfAudio):
        if(chunk.rms < rmsOfSilence and startSilence == False):
            #detecta um chunk que começa com silêncio
            startSilenceClipTime = currentTime
            startSilence = True
            if mode == "DEBUG":
                silenceFileTxt.write("Começou: " + str(currentTime) + ":" + str(chunk.rms) + ":" + str(round(chunk.dBFS, 2)) + "\n")
        elif(chunk.rms > rmsOfSilence and startSilence == True and startSilenceClipTime < currentTime - 1.5):
            #achou o fim de um chunk que possui no mínimo 2x segundos, sendo x o tamanho do chunk
            endSilenceClipTime = currentTime - (timeOfSilenceInMilliseconds / 1000.0)
            silenceClip = videoFile.subclip(startSilenceClipTime, endSilenceClipTime)
            silenceFilename = "silence" + str(fileCounter) + ".mp4"
            textClip = TextClip(silenceFilename, fontsize = 80)
            compClip = CompositeVideoClip([silenceClip, textClip]).set_duration(endSilenceClipTime - startSilenceClipTime)
            if mode == "DEBUG":
                if os.path.exists(silenceFilename) == False:
                    compClip.write_videofile(silenceFilename, logger = None)
            listOfClipsToCombine.append(compClip)

            startSilence = False
            fileCounter += 1
            if(mode == "DEBUG"):
                silenceFileTxt.write(silenceFilename + "\n")
            silenceToRemoveTxt.write(silenceFilename + ":" + str(startSilenceClipTime) + ":" + str(endSilenceClipTime) + "\n")
        elif(chunk.rms > rmsOfSilence and startSilence == True):
            #achou um chunk de exatamente x segundos, sendo x o tamanho do chunk. nesse caso ignora
            startSilence = False
            if(mode == "DEBUG"):
                silenceFileTxt.write("Interrompido: " + str(currentTime) + ":" + str(chunk.rms) + ":" + str(round(chunk.dBFS, 2)) + "\n")
        elif(it == len(chunksOfAudio) - 1):
            #última iteração
            if startSilence == True:
                endSilenceClipTime = currentTime - (timeOfSilenceInMilliseconds / 1000.0)
                silenceClip = videoFile.subclip(startSilenceClipTime)
                silenceFilename = "silence" + str(fileCounter) + ".mp4"
                textClip = TextClip(silenceFilename, fontsize = 80)
                compClip = CompositeVideoClip([silenceClip, textClip]).set_duration(endSilenceClipTime - startSilenceClipTime)
                if mode == "DEBUG":
                    if os.path.exists(silenceFilename) == False:
                        compClip.write_videofile(silenceFilename, logger = None)
                listOfClipsToCombine.append(compClip)

                #silenceFileTxt.write("Final: " + str(currentTime) + ":" + str(chunk.rms) + ":" + str(round(chunk.dBFS, 2)) + "\n")
                if(mode == "DEBUG"):
                    silenceFileTxt.write(silenceFilename)
                silenceToRemoveTxt.write(silenceFilename + ":" + str(startSilenceClipTime) + ":" + str(endSilenceClipTime))
        elif(startSilence == True):
            #fins de debug
            if(mode == "DEBUG"):
                silenceFileTxt.write(str(currentTime) + ":" + str(chunk.rms) + ":" + str(round(chunk.dBFS, 2)) + "\n")

        currentTime += round(timeOfSilenceInMilliseconds / 1000.0, 2)
        it += 1

    if os.path.exists("silence.mp4") == False and mode == "DEBUG":
        silenceClips = concatenate_videoclips(listOfClipsToCombine)
        silenceClips.write_videofile("silence.mp4")
        silenceClips.close()

    if(mode == "DEBUG"):
        silenceFileTxt.close()
    silenceToRemoveTxt.close()
    videoFile.close()

    if os.path.exists("silenceToRemoveCOPY.txt") == False:
        shutil.copyfile("silenceToRemove.txt", "silenceToRemoveCOPY.txt")

def clipSilenceBasedOnTxtFile(videoFilename, txtFile, mode = "DEBUG"):
    silenceToRemoveFile = open(txtFile, "r")
    videoFile = VideoFileClip(videoFilename)

    print(colored("Recortando momentos de silêncio do vídeo...", "green"))
    firstIt = True
    listOfClipsToCombine = []
    i = 0
    for line in list(silenceToRemoveFile):
        if line[0] == "#":
            continue

        file, startTime, endTime = line.rstrip().split(":")
        startTime = float(startTime)
        endTime = float(endTime)

        filename = "clip" + str(i) + ".mp4"
        if(startTime == 0.0 and firstIt == True):
            firstIt = False
            lastEndTime = endTime
        elif(firstIt == True):
            #from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
            #ffmpeg_extract_subclip(videoFilename, 0, startTime, targetname=filename)
            clip = videoFile.subclip(0, startTime)
            listOfClipsToCombine.append(clip)
            if mode == "DEBUG":
                clip.write_videofile(filename)
            lastEndTime = endTime
            firstIt = False
        else:
            #ffmpeg_extract_subclip(videoFilename, lastEndTime, startTime, targetname=filename)
            clip = videoFile.subclip(lastEndTime, startTime)
            listOfClipsToCombine.append(clip)
            if mode == "DEBUG":
                clip.write_videofile(filename)
            lastEndTime = endTime
        i += 1

    totalClips = i

    if os.path.exists("original_without_silence.mp4") == False:
        finalVideoClips = concatenate_videoclips(listOfClipsToCombine)
        finalVideoClips.write_videofile("original_without_silence.mp4")
        finalVideoClips.close()

    videoFile.close()
    silenceToRemoveFile.close()

def deleteTempFiles():
    for file in os.listdir(os.getcwd()):
        if file.endswith(".txt"):
            os.remove(file)
        if file.endswith(".mp4"):
            if "clip" in file:
                os.remove(file)
            if "silence" in file:
                os.remove(file)

def main():
    initializeMoviePy()

    #passe aqui o nome do arquivo de vídeo, o limiar que demarca intensidade de silêncio (900 é um bom valor) e oq seria uma boa
    #duração de silêncio (coloquei 250 ms alí)
    identifySilenceMomentsOfVideo("pythonfazpramim1-2.mp4", 900, 250, "RELEASE")

    #essa função abaixo clipa o vídeo original passado por parâmetro de acordo com a informação de silêncio no arquivo de log
    clipSilenceBasedOnTxtFile("pythonfazpramim1-2.mp4", "silenceToRemoveCOPY.txt", "RELEASE")

    deleteTempFiles()

if __name__ == "__main__":
    main()


# PyMovie.py

import os
import codecs
import json
import urllib
import argparse
import webbrowser
import re
import argparse
import webbrowser
import sys
import pandas as pd
import datetime
from pymediainfo import MediaInfo
from libs.html import *


# Sets up the logger that is used throughout the program as a means of tracking issues, successes, and metrics for each function.

import logging

logger = logging.getLogger('PyMovie')
hdlr = logging.FileHandler('Data/PyMovie_log.txt')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel("INFO")


# This function is used to clean up file names that may have dates, extraneous words in parentheses, etc. By normalizing the names, we hope to have greater success when querying the IMDB API.

def cleanTitle(filename):
    title = re.sub(r'\.(\w|\d){2,4}$',"",filename) #Remove file extension
    title = re.sub(r'(\(|\[)(.*)(\)|\])',"",title) #Remove anything in parentheses or brackets
    title = re.sub(r'\:',"",title) #Remove Colons
    title = re.sub(r'(\s)?\-(\s)?'," ",title) #Remove hyphens for subtitles
    title = re.sub(r'(\s)[0-9]{1,2}(\s)', ' ',title) #Remove Numeric identifiers
    title = title.strip() #Trim Whitespace
    return title    


# This function takes a directory name and ensure it ends with a slash (i.e., "/"). This keeps the later functions from throwing errors.

def dirClean(directory_name):
    if directory_name[-1] != "/":
        directory_name = directory_name + "/"
    return(directory_name)


# This function reads the names of files in a provided directory and then runs those files through the IMDB API to collect movie information.  The final output are two .csv files; one for movies that were found through the API and another for files that weren't found.  This function also checks against previous runs of the function to limit the number of API calls.  Finally, this function downloads and stores movie poster artwork for later use in web page construction.

def crawl(source_dir):
    begin = datetime.datetime.now() #For recording runtime
    logger.info('crawl() START')
    
    source_dir = dirClean(source_dir)
    movie_list = os.listdir(source_dir)
    columns = ['ID','title','year','director','actors','plot','genre_primary','genre_other','poster','rating_imdb','rating_metacritic','rating_rotten','filename','filesize','duration','resolution','aspect']
    
    startposters = len(os.listdir("./Site/pages/posters/"))
    
    #Attempt to load existing data. If it is not there, create empty dataframe instead
    if os.path.exists("Data/movieDF.csv"):
        movieDF = pd.read_csv("Data/movieDF.csv")
        startrows = len(movieDF)
        if os.path.exists("Data/failedmovieDF.csv"):
            moviefailDF = pd.read_csv("Data/failedmovieDF.csv")
        else:
            moviefailDF = pd.DataFrame(columns = ['title'])
        #Remove rows from movieDF for movies that no longer appear in the directory
        for movie in movieDF['filename']:    
            if movie not in movie_list:
                movieDF = movieDF[movieDF.filename != movie]
                logger.info("Removed " + movie + " from movie library.")
                #Remove photos for movies that no longer appear in the directory
                title = cleanTitle(movie)
                if title + '.jpg' in os.listdir("./Site/pages/posters/"):
                    os.remove('./Site/pages/posters/' + title + '.jpg')
                    logger.info('Removed ' + title + '.jpg from poster folder.')
                if title + '.html' in os.listdir("./Site/pages/"):
                    os.remove('./Site/pages/' + title + '.html')
                    logger.info('Removed ' + title + '.html from webpages folder.')
    else: 
        movieDF = pd.DataFrame(columns=columns)
        moviefailDF = pd.DataFrame(columns = ['title'])
        startrows = len(movieDF)
    
    for movie in movie_list:
                # The following 2 lines may need to be hacked at dependent of naming
                # Scheme. Or, a more dynamic solution may be needed to suffice.
                movieInfo = pd.DataFrame(columns=columns)
                title = cleanTitle(movie[0:])
                
                #If movie is already in the dataframe than skip to the next iteration of the loop
                if title in movieDF['title'].values:
                    #If movie poster isn't downloaded, then download it based on stored URL
                    if title + '.jpg' not in os.listdir("./Site/pages/posters/"):
                            os.system('wget -O "Site/pages/posters/' + title + '.jpg" ' + movieDF.loc[movieDF['title'] == title, 'poster'].values[0])
                    continue
                
                try:
                    # Using API from http://www.omdbapi.com/
                    url = "http://www.omdbapi.com/?t=" + urllib.parse.quote(title) + '&tomatoes=true'
                    # Now dowloading and parsing the results as json file so we can work on it locally
                    reader = codecs.getreader("utf-8")
                    data = json.load(reader(urllib.request.urlopen(url)))

                    try:
                        movie_imdbID = data["imdbID"]
                        movie_title = data["Title"]
                        movie_year = data["Year"]
                        movie_director = data["Director"]
                        movie_actors = data["Actors"]
                        movie_plot = data["Plot"]
                        movie_genre_1 = data["Genre"].split(",")[0]
                        movie_genre_2 = data["Genre"].split(",")[1:]
                        movie_poster = data["Poster"]
                        
                        #If poster file doesn't exist in image directory then download it based on API URL
                        if title + '.jpg' not in os.listdir("./Site/pages/posters/"):
                            filename = title
                            os.system('wget -O "Site/pages/posters/' + filename + '.jpg" ' + movie_poster)
                        
                        movie_rating_imdb = data["imdbRating"]
                        movie_rating_metacritic = data["Metascore"]
                        movie_rating_rotten = data["tomatoMeter"]
                        movie_filename = movie
                        
                        media_info = MediaInfo.parse(source_dir + movie)

                        movie_filesize = media_info.tracks[0].other_file_size[0]
                        movie_duration = media_info.tracks[0].other_duration[2]
                        movie_resolution = str(media_info.tracks[1].sampled_width + " * " + media_info.tracks[1].sampled_height)
                        movie_aspect = media_info.tracks[1].other_display_aspect_ratio[0]

                        movieInfo.loc[1] = [movie_imdbID, movie_title, movie_year, movie_director, movie_actors, movie_plot, movie_genre_1,movie_genre_2,
                                                  movie_poster, movie_rating_imdb, movie_rating_metacritic, movie_rating_rotten,
                                            movie_filename, movie_filesize, movie_duration, movie_resolution, movie_aspect]

                   
                        movieDF = movieDF.append(movieInfo)
                        logger.info("Success - " + movie)
                        logger.info("Success URL: " + url)   
                        
                    except Exception as e:
                        failMovie = pd.DataFrame(columns=['title'])
                        failMovie.loc[1] = title
                        moviefailDF = moviefailDF.append(failMovie)
                        print(e)
                        logger.info("Failed - " + movie)
                        logger.info("Fail URL: " + url) 
                        pass
                except Exception as e:
                    print(e)
    movieDF = movieDF.sort_values(by='title')
    movieDF.to_csv('Data/movieDF.csv',index=False)
    moviefailDF.to_csv('Data/failedmovieDF.csv',index=False)
    
    #write to Logger
    run_columns = ['date','time','runtime','movie_delta','movie_total','poster_delta','poster_total']
    
    if os.path.exists("Data/runData.csv"):
        run_data = pd.read_csv("Data/runData.csv")
    else: 
        run_data = pd.DataFrame(columns=run_columns)
        
    end = datetime.datetime.now()
    endrows = len(movieDF)
    endposters = len(os.listdir("./Site/pages/posters/"))
    now = datetime.datetime.now()
    
    runInfo = pd.DataFrame(columns=run_columns)
    runInfo.loc[1] = [now.strftime('%Y-%m-%d'),now.strftime('%H:%M:%S'),end-begin, 0-(startrows-endrows),endrows,
                     0-(startposters-endposters), endposters]
    run_data = run_data.append(runInfo)
    run_data.to_csv('Data/runData.csv',index=False)
    
    logger.info('Crawl() function complete')
    print("crawl() END")


# This function creates a website that has a main page that displays movie posters and names and then subpages for each movie that was successfully found through the IMDB API. Added a jquery table that allows the user to sort and search for movies based on title, genre and rating.

def htmlout(movie_file, source_dir):
    logger.info('htmlout() START')
    
    movieDF = pd.read_csv("Data/" + movie_file)
    output_file = "Site/movies.html"
            
    try:
        # Opening and generating final html (for example movies.html) file
        html_file = open(output_file, "w")
        html_file.write(header)
        html_file.write('<div class="medium-12 columns">')
        html_file.write('<h1 style="color:white" class="titleshadow">PyMovie Share</h1>')
        html_file.write('<hr class="style-four"></div>')
        html_file.write('<div class="row">')
        
        #Write Table Data
        html_file.write('<table id="movieTable" class="display" cellspacing="0" width="100%">')
        html_file.write('<thead style="font-size:125%"><tr><th rowspan="2"></th><th rowspan="2">Title</th><th rowspan="2">Genre</th><th colspan="3"><center>Ratings</center></th><th rowspan="2">Actors</th></tr>')
        html_file.write('<tr><th>IMDB</th><th>Metacritic</th><th>Rotten Tomatoes</th></tr></thead><tbody>')

        for index, row in movieDF.iterrows():
            html_file.write('<tr>')
            html_file.write('<td><div class="face pic"><a href="./pages/' + row['title'] + '.html"><img src="pages/posters/' + row['title'] + '.jpg" style="height:100%;width:200px;box-shadow: 4px 4px 2px #9a9a9a"></a></div></td>')
            html_file.write('<td><a href="./pages/' + row['title'] + '.html" style="font-size:175%">' + row['title'] +'</a></td>')
            html_file.write('<td style="font-size:125%; text-align:center">' + row['genre_primary'] +'</td>')
            html_file.write('<td style="font-size:135%; text-align:center">' + str(row['rating_imdb']) +'</td>')
            html_file.write('<td><center>')
            
            if row['rating_metacritic'] <= 20: 
                html_file.write('<span class="metalow">' + str(int(row['rating_metacritic']))+'</span></center></td>')
            elif 20 < row['rating_metacritic'] <= 40: 
                html_file.write('<span class="metamedlow">' + str(int(row['rating_metacritic']))+'</span></center></td>')   
            elif 40 < row['rating_metacritic'] <= 60: 
                html_file.write('<span class="metamedium">' + str(int(row['rating_metacritic']))+'</span></center></td>')    
            elif 60 < row['rating_metacritic'] <= 80: 
                html_file.write('<span class="metamedhigh">' + str(int(row['rating_metacritic']))+'</span></center></td>')    
            elif row['rating_metacritic'] > 80: 
                html_file.write('<span class="metahigh">' + str(int(row['rating_metacritic']))+'</span></center></td>') 
            else:
                html_file.write('<span class="metaNA">NA</span></center></td>')
            
            html_file.write('<td style="font-size:135%; text-align:center">' + str(row['rating_rotten']) + ' ')
            
            if row['rating_rotten'] < 60: 
                html_file.write('<img src="pages/images/rottenicon.png" style="width:30px; display:inline"></div></td>') 
            elif row['rating_rotten'] >= 60: 
                html_file.write('<img src="pages/images/freshicon.png" style="width:30px; display:inline"></div></td>')
            else:
                html_file.write('</td></tr>')
        
            html_file.write('<td>' + row['actors'] +'</td></tr>')
        
        #Close Table
        html_file.write('</tbody></table>')
        
        # Generate some stats at on the bottom of the html page
        html_file.write('<div class="row">')
        html_file.write('<hr>')
        
        html_file.write(footer)
        html_file.close()
        logger.info("Homepage Complete")
        
        for index, row in movieDF.iterrows():
            movie_page = "./Site/pages/" + row['title'] + ".html"     
            html_file = open(movie_page, "w")
            html_file.write(header_sub)
            
            html_file.write('<div class="fixed"><a href="../movies.html"><img src="images/backarrow.png" style="width:80px"></a></div><div class="row">')
            html_file.write('<h1 style="color:white; display:inline" class="titleshadow" id="movie">' + row['title'] + ' (' + str(row['year']) +')</h1>')
            html_file.write('<hr class="style-four"></div>')
            html_file.write('<div class="row">')
            html_file.write('<div class="medium-5 columns">')
            html_file.write('<div class="panel">')
            html_file.write('<img src="posters/' + row['title'] + '.jpg" style="height:100%;width:375px;box-shadow: 5px 5px 2px #474747"/>')
            html_file.write('</div></div>')
            html_file.write('<div class="medium-7 columns">')
            html_file.write('<div class="panel">')
            html_file.write('<div class="medium-4 columns" style="border-right:1px solid #c7c9cc;height:90px">')
            html_file.write('<center><p style="font-size:125%; padding-bottom: 20px"><b>IMDB</b><br> ' + str(row['rating_imdb']) + '/10</p></center>')
            html_file.write('<vr>')
            html_file.write('</div><div class="medium-4 columns" style="border-right:1px solid #c7c9cc;height:100px">')
            html_file.write('<center><div style="font-size:125%; padding-bottom: 10px"><b>Metacritic</b></div>')
                            
            if row['rating_metacritic'] <= 20: 
                html_file.write('<span class="metalow">' + str(int(row['rating_metacritic']))+'</span></center>')
            elif 20 < row['rating_metacritic'] <= 40: 
                html_file.write('<span class="metamedlow">' + str(int(row['rating_metacritic']))+'</span></center>')   
            elif 40 < row['rating_metacritic'] <= 60: 
                html_file.write('<span class="metamedium">' + str(int(row['rating_metacritic']))+'</span></center>')    
            elif 60 < row['rating_metacritic'] <= 80: 
                html_file.write('<span class="metamedhigh">' + str(int(row['rating_metacritic']))+'</span></center>')    
            elif row['rating_metacritic'] > 80: 
                html_file.write('<span class="metahigh">' + str(int(row['rating_metacritic']))+'</span></center>') 
            else:
                html_file.write('<span class="metaNA">NA</p></center>')
            
            html_file.write('</div>')
            html_file.write('<center><p style="font-size:125%; padding-bottom: 20px"><b>Rotten Tomatoes</b><br> ' + str(row['rating_rotten']) + ' ')
            
            if row['rating_rotten'] < 60: 
                html_file.write('<img src="images/rottenicon.png" style="width:30px; display:inline"></p></center>') 
            elif row['rating_rotten'] >= 60: 
                html_file.write('<img src="images/freshicon.png" style="width:30px; display:inline"></p></center>')
            else:
                html_file.write('</td></tr>')

            html_file.write('<hr>')
            
            html_file.write('<p><b>Plot:</b> ' + str(row['plot']) + '</p>')
            html_file.write('<p><b>Actors:</b> ' + str(row['actors']) + '</p>')
            html_file.write('<p><b>Director:</b> ' + str(row['director']) + '</p>')
            
            html_file.write('<hr>')
            html_file.write('<div class="medium-4 columns">')
            html_file.write("<p><b>Runtime:</b> " + str(row['duration']) + "</p>")
            html_file.write('</div><div class="medium-4 columns">')
            html_file.write("<p><b>Filesize:</b> " + str(row['filesize']) + "</p>")
            html_file.write('</div>')
            html_file.write("<p><b>Resolution:</b> " + str(row['resolution']) + "</p>")
            html_file.write('<hr>')
            html_file.write(
                '<a href="file://' + dirClean(source_dir) + row['filename'] + '" download class="button large radius success expand" onclick="dnld();">Download</a>') 
            html_file.write("</div></div></div>")

            html_file.write(footer_sub)
            html_file.close()
            logger.info("Success - " + row['title'] + '.html')
        
        # Opening the browser and presenting the summary html page
        webbrowser.open('file://' + os.path.realpath(output_file))
    except Exception as e:
        print(e)
        print("***** Error. Maybe try to run the script again but bit later? *****")
        logger.critical('Critical error -- Abort Script')
        sys.exit(0)
        
    #write to Logger
    logger.info('htmlout() function complete')
    print("htmlout() END")



import io
from typing import Final

import update as update
from telegram import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
import networkx as nx
from collections import defaultdict
import db
from utils import *
from tmdbv3api import Movie
from secret import TOKEN, TMDB_API_KEY, BOT_USERNAME
# pip install python-telegram-bot
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from Movies import get_movies_list

print('Starting up bot...')
db.db_create_tables() # create the DB tables

user_preferences = {}
userp = []

# createa a genres dictionary with genre name and its integer value
genres_dict = create_genre_dictionary()


# Method to rate a movie using the TMDB API
def rate_movie(movie_name, rating):

    """
    Rate a movie using the TMDB API.

    :param movie_name: The name of the movie to be rated.
    :param rating: The rating to be given to the movie (between 1 and 10).
    """
        
    # create a new guest session
    guest_session_request = requests.get(
        f"https://api.themoviedb.org/3/authentication/guest_session/new?api_key={TMDB_API_KEY}")

    # get the guest session id to pass it to the API post
    GUEST_SESSION_ID = guest_session_request.json()['guest_session_id']

    # get the movie's id from its name
    movie_id = get_movie_id(movie_name)

    rating_url = f'https://api.themoviedb.org/3/movie/{movie_id}/rating'

    headers = {
        'Content-Type': 'application/json;charset=utf-8'
    }

    rating = {
        'value': rating
    }

    params = {
        'api_key': TOKEN,
        'guest_session_id': GUEST_SESSION_ID
    }

    # rate the movie with headers as required
    rate_response = requests.post(rating_url, headers=headers, json=rating, params=params)

    if (rate_response.status_code == 201):
        print(f"Movie {movie_name} was rated {rating['value']} successfully!")

    else:
        print("Failed to submit movie rating")


# method to get top rated movies or upcoming
def get_movies_by_options(option):

    """
    Get a list of movies based on a specified option.

    :param option: The option for fetching movies (e.g., 'top_rated', 'upcoming').
    :return: A list of movie names.
    """
        
    discover_options = ['top_rated', 'upcoming']

    # Make a request to the TMDB API to fetch movies
    response = requests.get(f"https://api.themoviedb.org/3/movie/{option}?api_key={TMDB_API_KEY}&language=en-US")
    movies = response.json()['results']

    movies_list = []
    
    # Extract relevant movie details and create a list of movie names
    i = 0
    while i < 20:
        if(movies[i]['original_language'] == 'en'): #add a movie only if it's in english

            movie_details = {
            'title': movies[i]['original_title'],
            'genres': [genres_dict[genre_id] for genre_id in movies[i]['genre_ids']],
            'release_year': movies[i]['release_date'][:4],
            'duration': f"{movies[i]['runtime'] // 60}h {movies[i]['runtime'] % 60}m",
            'actors': get_film_actors(get_movie_id(movies[i]['title']))
            }

            movies_list.append(movie_details)
            
        i += 1

    return movies_list

# method to calculate similarity between movies based on genres, release year, cast and duration
def calculate_similarity(target_params, movie_params):

    """
    Calculate the similarity score between two sets of movie parameters.

    :param target_params: Parameters of the target movie.
    :param movie_params: Parameters of the movie to compare.
    :return: The similarity score.
    """
        
    # Each parameter is a set of values
    genre_diff = len(target_params[0].intersection(movie_params[0]))
    year_diff = abs(target_params[1] - movie_params[1])
    actor_diff = len(target_params[2].intersection(movie_params[2]))
    duration_diff = abs(target_params[3] - movie_params[3])

    # Calculate a weighted similarity score
    similarity_score = genre_diff + year_diff + actor_diff + duration_diff

    return similarity_score

# Method to discover movies based on user-defined parameters
def discover_movie(genre_name=None, release_year=None, actor_name=None, duration=None):

    """
    Discover movies based on user-defined parameters.

    :param genre_name: The genre of the movie.
    :param release_year: The release year of the movie.
    :param actor_name: The actor's name in the movie.
    :param duration: The duration of the movie.
    :return: A network graph containing movie information.
    """
        
    total_films_added = 0
    NUMBER_OF_FILMS_TO_ADD = 10

    DISCOVER_URL = "https://api.themoviedb.org/3/discover/movie"

    # Initialize a network graph to store movie information
    filmGraph = nx.Graph()
    actor_id = get_actor_id(actor_name) if actor_name is not None else None
    genre_id = genres_dict.get(genre_name) if genre_name is not None else None

    # Iterate through multiple pages of results
    page = 1
    while total_films_added < NUMBER_OF_FILMS_TO_ADD and page <= 500:

        # Prepare parameters for the TMDB API request
        params = {
            "api_key": TMDB_API_KEY,
            "primary_release_year": release_year,
            "with_genres": genre_id,
            "with_cast": actor_id,
            "sort_by": "popularity.desc",
            "include_adult": False,
            "include_video": False,
            "runtime.gte": duration,
            "page": page
        }

        # Make the request to TMDB API
        response = requests.get(DISCOVER_URL, params=params)

        if response.status_code == 200:
            movies = response.json()["results"]
            for movie in movies:
                if total_films_added >= NUMBER_OF_FILMS_TO_ADD:
                    break
                
                # Extract movie details and add to the graph
                film_id = get_movie_id(movie['title'])
                film_runtime = get_film_runtime(film_id)
                duration_formatted = f"{film_runtime // 60}h {film_runtime % 60}m"

                filmGraph.add_node(
                    movie['title'],
                    category=movie['genre_ids'],
                    release_year=movie['release_date'][:4],
                    duration=duration_formatted,
                    actor=get_film_actors(film_id)
                )

                total_films_added += 1

        else:
            print(f"Error fetching data from API - {response.status_code}")
            print(response.text)
            break

        page += 1

    # If we have less than 10 movies, fill the list with closest matches
    if total_films_added < NUMBER_OF_FILMS_TO_ADD:
        movie_similarity = defaultdict(list)
        target_params = (genre_id, release_year, actor_id, duration)

        for movie in filmGraph.nodes(data=True):
            params = (
                set(movie[1]['category']),
                int(movie[1]['release_year']),
                set(movie[1]['actor']),
                movie[1]['duration']
            )

            similarity = calculate_similarity(target_params, params) 
            movie_similarity[similarity].append(movie)

        # Find closest movies and add them to the result
        sorted_similarities = sorted(movie_similarity.keys(), reverse=True)
        for similarity in sorted_similarities:
            for movie in movie_similarity[similarity]:
                if total_films_added >= NUMBER_OF_FILMS_TO_ADD:
                    break

                filmGraph.add_node(movie[0], **movie[1])
                total_films_added += 1

    return filmGraph



async def inline_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()  # Await the answer() function to properly remove the "loading" icon

    option = query.data

    if option == "upcoming":
        fof = get_movies_by_options('upcoming')
        await query.message.reply_text(fof)

    elif option == "ratemovies":
        await query.message.reply_text("What's the name of the movie you want to rate?")
        context.user_data['rating_movie_name'] = True
        context.user_data.pop('rating_movie_number_input', None)

    elif option == "searchmovie":
        await query.message.reply_text("Type movie to start the search!")

    elif option == "topmovies":
        fof = get_movies_by_options('top_rated')
        await query.message.reply_text(fof)

    elif option == 'randommovies':
        genre_dict = {v: k for k, v in genres_dict.items()}
        movies = discover_movie(None, None, None, None)
        if movies:
            for movie in movies.nodes(data=True):
                title = movie[0]
                details = movie[1]
                release_year = details.get('release_year', 'Unknown')
                duration = details.get('duration', 'Unknown')
                genre_names = ', '.join(
                    [genre_dict.get(category) for category in details['category'] if category in genre_dict])

                actors = ', '.join(details['actor'])
                poster_url = get_movie_image_url(TMDB_API_KEY, title)
                response = requests.get(poster_url)
                image = io.BytesIO(response.content)
                image.name = "movie_poster.jpg"

                details_str = f"Release Year: {release_year}\nDuration: {duration}\nGenres: {genre_names}\nActors: {actors}"
                await query.message.reply_photo(photo=image, caption=details_str)
        else:
            response = 'No movies found.'

    elif option == "history":
        history = db.get_user_recent_searches(query.message.chat.id)
        sos = ""
        for h in history:
            sos = sos + " " + h[2]
        await query.message.reply_text(sos)

# use the /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """
    Handle the /start command to initiate a conversation with the bot.

    :param update: The update object containing the /start command.
    :param context: The context object containing user context data.
    """
    
    # Create an inline keyboard for user interaction
    keyboard = [
        [InlineKeyboardButton("Upcoming", callback_data="upcoming")],
        [InlineKeyboardButton("Top Movies", callback_data="topmovies")],
        [InlineKeyboardButton("History", callback_data="history")],
        [InlineKeyboardButton("Random Movies", callback_data="randommovies")],
        [InlineKeyboardButton("Rate Movies", callback_data="ratemovies")],
        [InlineKeyboardButton("Search Movie", callback_data="searchmovie")]
    ]

    # Build the reply markup
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send a welcome message to the user
    await update.message.reply_text(
        "Hello there! I'm a bot. What's up?",
        reply_markup=reply_markup
    )


# use the /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Try typing anything and I will do my best to respond!')


# use the /custom command
async def topmovies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fof = get_movies_by_options('top_rated')
    await update.message.reply_text(fof)

# use the /about command
async def About_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hi, Im a bot that searches for you the movies that will suit you best')

# use the /history command
async def History_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = db.get_user_recent_searches(update.message.chat.id)
    sos = ""
    for h in history:
        sos = sos +" " + h[2]

    await update.message.reply_text(sos)

# use the /upcoming command
async def UpComing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fof = get_movies_by_options('upcoming')
    await update.message.reply_text(fof)


def handle_response(text: str) -> str:
    
    processed: str = text.lower()
    return 'I don\'t understand'


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """
    Handle user messages and initiate a conversation with the bot.

    :param update: The update object containing the user's message.
    :param context: The context object containing user context data.
    """
        
    message_type: str = update.message.chat.type
    text: str = update.message.text
    if not text:  # Check if the message text is empty
        return
    
    response = ''  # initialize the response variable

    # Check if the user is in a specific conversation state
    if context.user_data.get('rating_movie_name'):
        # User entered a movie name
        movie_name = update.message.text
        context.user_data['rating_movie_name'] = False  # Reset the flag
        context.user_data['rating_movie_name_input'] = movie_name
        print(context.user_data.get('rating_movie_name_input'))
        # Save the movie name
        await update.message.reply_text("Type a number between 1 and 10 to rate this movie.")

    elif context.user_data.get('rating_movie_name_input'):
        # User entered a rating for a movie
        rating = update.message.text

        # ensure the rating is a number between 1 and 10
        if rating.isdigit() and 1 <= int(rating) <= 10:
            # Clear the saved input
            await update.message.reply_text(
                f"You rated '{context.user_data['rating_movie_name_input']}' with a rating of {rating}.")
            rate_movie(context.user_data['rating_movie_name_input'], float(rating))
            # context.user_data.pop('rating_movie_name_input')
            # context.user_data.pop('rating_movie_name')
            context.user_data['rating_movie_name_input'] = False
            print(context.user_data.get('rating_movie_name_input'))

        else:
            await update.message.reply_text("Please provide a valid rating between 1 and 10.")

        # Clear the saved data
        # context.user_data.pop('rating_movie_name_input')

    if message_type == 'private': # User is sending a private message
        
        user_id = update.message.chat.id
        user_pref = user_preferences.get(user_id, {})

        if text.lower() == 'movie':
            # User wants to search for a movie

            user_pref['movie_search'] = 'genre'
            user_preferences[user_id] = user_pref
            await update.message.reply_text('Please enter the genre of the movie:')

        elif user_pref.get('movie_search'):
            # User is in the process of movie search

            search_step = user_pref['movie_search']

            if search_step == 'genre': # User is selecting the genre of the movie
                user_pref['genre'] = text
                user_pref['movie_search'] = 'year'
                await update.message.reply_text('Please enter the release year:')

            elif search_step == 'year': # User is selecting the release year of the movie
                user_pref['year'] = text
                user_pref['movie_search'] = 'duration'
                await update.message.reply_text('Please enter the duration (in minutes):')

            elif search_step == 'duration': # User is selecting the duration of the movie
                user_pref['duration'] = text
                user_pref['movie_search'] = 'actor'
                await update.message.reply_text('Please enter the actor:')

            elif search_step == 'actor': # User is selecting the actor of the movie
                user_pref['actor'] = text
                user_pref.pop('movie_search')  # Clear movie search step
                user_preferences[user_id] = user_pref

                # Fetch movies based on user preferences
                genre_name = user_pref['genre']
                release_year = user_pref['year']
                duration = user_pref['duration']
                actor_name = user_pref['actor']

                if(not db.db_user_exists(user_id)): #if user searches for first time then add user to db
                    db.db_add_user(user_id)

                # insert user's recent search 
                sos = db.db_add_recent_search(user_id, genre_name, release_year, duration, actor_name)

                # Fetch movies and their image URLs
                genre_dict = {v: k for k, v in genres_dict.items()} # createa a reverse look-up dictionary
                movies = discover_movie(genre_name, release_year, duration, actor_name)

                if movies:
                    for movie in movies.nodes(data=True):
                        title = movie[0]
                        details = movie[1]
                        release_year = details.get('release_year', 'Unknown')
                        duration = details.get('duration', 'Unknown')
                        genre_names = ', '.join(
                            [genre_dict.get(category) for category in details['category'] if category in genre_dict])

                        actors = ', '.join(details['actor'])
                        poster_url = get_movie_image_url(TMDB_API_KEY,title)
                        response = requests.get(poster_url)
                        image = io.BytesIO(response.content)
                        image.name = "movie_poster.jpg"

                        details_str = f"Release Year: {release_year}\nDuration: {duration}\nGenres: {genre_names}\nActors: {actors}"
                        await update.message.reply_photo(photo=image, caption=details_str)
                else:
                    response = 'No movies found.'

            else:
                response = 'I don\'t understand'

    # Reply normally if the message is in private
    print('Bot:', response)
    await update.message.reply_text(response)

# Log errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):

    """
    Handle errors that occur during the bot's operation.

    :param update: The update object containing the error.
    :param context: The context object containing error context data.
    """
        
    print(f'Update {update} caused error {context.error}')


# Run the program
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('about', About_command))
    app.add_handler(CommandHandler('history', History_command))
    app.add_handler(CommandHandler('upcoming', UpComing_command))
    app.add_handler(CommandHandler('topmovies', topmovies_command))
     # app.add_handler(MessageHandler(filters.TEXT, rate_movie_number))
    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(inline_button_callback))
    # Log all errors
    app.add_error_handler(error)

    print('Polling...')
    # Run the bot
    app.run_polling(poll_interval=5)

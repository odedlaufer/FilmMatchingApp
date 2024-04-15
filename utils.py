import requests
from secret import TOKEN
from PIL import Image
from io import BytesIO

# Method to get the ID of an actor using their name
def get_actor_id(actor_name):

    """
    Get the ID of an actor based on their name using The Movie Database (TMDb) API.
    Args:
        actor_name (str): The name of the actor.
    Returns:
        int: The actor's ID if found, otherwise None.
    """
        
    actor_response = requests.get(f"https://api.themoviedb.org/3/search/person?api_key={TOKEN}&query={actor_name}")
    actor_data = actor_response.json()

    if actor_data['total_results'] == 0:
        print("No results found for that actor.")
        return
    else:
        actor_id = actor_data['results'][0]['id']
        return actor_id

# Method to get the ID of a movie using its name
def get_movie_id(movie_name):

    """
    Get the ID of a movie based on its name using The Movie Database (TMDb) API.
    Args:
        movie_name (str): The name of the movie.
    Returns:
        int: The movie's ID if found, otherwise None.
    """

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TOKEN}&query={movie_name}"
    response = requests.get(url)

    if(response.status_code == 200):
        data = response.json()

        if(data['total_results'] > 0):
            movie_id = data['results'][0]['id']
            return movie_id
        else:
            print(f"No movie found with the name {movie_name}")
    else:
        print(f"Error retrieving movie information.\nResponse status code: {response.status_code}")

# Method to get the URL of a movie's image
def get_movie_image_url(api_key, movie_name):

    """
    Get the URL of a movie's image (poster) using The Movie Database (TMDb) API.
    Args:
        api_key (str): TMDb API key.
        movie_name (str): The name of the movie.
    Returns:
        str: The URL of the movie's image, or None if not found.
    """
        
    base_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": api_key,
        "query": movie_name
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if "results" in data and len(data["results"]) > 0:
        # Assuming the first result is the closest match
        movie_id = data["results"][0]["id"]

        # Get details of the movie
        movie_details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {
            "api_key": api_key
        }

        movie_response = requests.get(movie_details_url, params=params)
        movie_data = movie_response.json()

        if "poster_path" in movie_data:
            image_url = f"https://image.tmdb.org/t/p/original{movie_data['poster_path']}"
            return image_url

    return None

# Method to get the runtime of a film using its ID
def get_film_runtime(film_id):

    """
    Get the runtime of a film using its ID from The Movie Database (TMDb) API.
    Args:
        film_id (int): The ID of the film.
    Returns:
        int: The runtime of the film in minutes.
    """
        
    response = requests.get(f"https://api.themoviedb.org/3/movie/{film_id}?api_key={TOKEN}&language=en-US")
    movie_details = response.json()
    runtime = movie_details['runtime']
    return runtime

# Method to get the actors of a film using its ID
def get_film_actors(film_id):

    """
    Get the actors of a film using its ID from The Movie Database (TMDb) API.
    Args:
        film_id (int): The ID of the film.
    Returns:
        list: A list of actor names (up to 2 actors).
    """

    CAST_URL = f"https://api.themoviedb.org/3/movie/{film_id}/credits"

    params = {"api_key": TOKEN}

    response = requests.get(CAST_URL, params=params)

    if response.status_code == 200:
        cast = response.json()["cast"]
        return [actor["name"] for actor in cast[:2]]

    return []

# Method to get the URL of a movie's poster
def get_movie_poster(movie_name):

    """
    Get the URL of a movie's poster image using The Movie Database (TMDb) API.
    Args:
        movie_name (str): The name of the movie.
    Returns:
        str: The URL of the movie's poster image, or None if not found.
    """
        
    movie_id = get_movie_id(movie_name)
    response = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/images?api_key={TOKEN}")

    if response.status_code == 200:
        data = response.json()
        poster_path = data['posters'][0]['file_path']
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
        return poster_url
    else:
        print(f"Error: {response.status_code} - {response.reason}")
        return None


# Method to create a dictionary of movie genres
def create_genre_dictionary():

    """
    Create a dictionary of movie genres using The Movie Database (TMDb) API.
    Returns:
        dict: A dictionary with genre names as keys and genre IDs as values.
    """
        
    response = requests.get(f"https://api.themoviedb.org/3/genre/movie/list?api_key={TOKEN}")
    genres = response.json()['genres']

    genres_dict = {genre["name"]: genre["id"] for genre in genres}
    return genres_dict
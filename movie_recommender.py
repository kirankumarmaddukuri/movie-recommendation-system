import pandas as pd
import ast
import requests
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def load_data():
    try:
        movies = pd.read_csv('movies_metadata.csv', low_memory=False)
        credits = pd.read_csv('credits.csv')
        keywords = pd.read_csv('keywords.csv')
        # Ensure id is string for all
        movies['id'] = movies['id'].astype(str)
        credits['id'] = credits['id'].astype(str)
        keywords['id'] = keywords['id'].astype(str)
        # Merge all on id
        movies = movies.merge(credits, on='id')
        movies = movies.merge(keywords, on='id')
        # Keep only relevant columns
        movies = movies[['id','title','overview','genres','keywords','cast','crew','vote_average','release_date','vote_count']]
        movies.dropna(subset=['title','overview','genres','keywords','cast','crew','vote_average','release_date'], inplace=True)
        # Keep only the top 5000 most popular movies
        movies = movies.sort_values('vote_count', ascending=False).head(5000).reset_index(drop=True)
        return movies
    except Exception as e:
        raise RuntimeError(f"Error loading data: {e}")

def convert(text):
    try:
        # Some columns are stringified lists of dicts
        if pd.isna(text) or text == '[]':
            return []
        return [d['name'] for d in ast.literal_eval(text)]
    except:
        return []

def fetch_director(text):
    try:
        if pd.isna(text) or text == '[]':
            return []
        L = []
        for i in ast.literal_eval(text):
            if isinstance(i, dict) and i.get('job') == 'Director':
                L.append(i['name'])
        return L
    except:
        return []

def collapse(L):
    L1 = []
    for i in L:
        L1.append(i.replace(" ", ""))
    return L1

def preprocess(movies):
    movies['genres'] = movies['genres'].apply(convert)
    movies['keywords'] = movies['keywords'].apply(convert)
    movies['cast'] = movies['cast'].apply(convert)
    movies['cast'] = movies['cast'].apply(lambda x: x[:3])
    movies['crew'] = movies['crew'].apply(fetch_director)
    movies['cast'] = movies['cast'].apply(collapse)
    movies['crew'] = movies['crew'].apply(collapse)
    movies['genres'] = movies['genres'].apply(collapse)
    movies['keywords'] = movies['keywords'].apply(collapse)
    movies['overview'] = movies['overview'].apply(lambda x: x.split() if isinstance(x, str) else [])
    movies['tags'] = movies['overview'] + movies['genres'] + movies['keywords'] + movies['cast'] + movies['crew']
    movies['tags'] = movies['tags'].apply(lambda x: " ".join(x))
    return movies

def create_similarity(movies):
    cv = CountVectorizer(max_features=5000, stop_words='english')
    vector = cv.fit_transform(movies['tags']).toarray()
    similarity = cosine_similarity(vector)
    return similarity

def get_movie_poster(movie_title, api_key, poster_cache=None):
    if poster_cache is not None and movie_title in poster_cache:
        return poster_cache[movie_title]
    try:
        if not api_key or api_key.strip() == "":
            return None
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': api_key.strip(),
            'query': movie_title,
            'language': 'en-US',
            'page': 1
        }
        for attempt in range(3):
            try:
                response = requests.get(search_url, params=params, timeout=15)
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    if results:
                        poster_path = results[0].get('poster_path')
                        if poster_path:
                            poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}"
                            if poster_cache is not None:
                                poster_cache[movie_title] = poster_url
                            return poster_url
                    break
                else:
                    break
            except Exception:
                if attempt < 2:
                    continue
    except Exception:
        pass
    if poster_cache is not None:
        poster_cache[movie_title] = None
    return None

def get_movie_details(movie_title, api_key):
    try:
        if not api_key or api_key.strip() == "":
            return None
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': api_key.strip(),
            'query': movie_title,
            'language': 'en-US',
            'page': 1
        }
        for attempt in range(3):
            try:
                response = requests.get(search_url, params=params, timeout=15)
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    if results:
                        return results[0]
                    break
                else:
                    break
            except Exception:
                if attempt < 2:
                    continue
    except Exception:
        pass
    return None

def recommend(movie, movies, similarity, num_recommendations=5):
    if movie not in movies['title'].values:
        return []
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommended_movies = []
    seen_titles = set()
    for i in distances[1:]:
        movie_data = movies.iloc[i[0]]
        title = movie_data.title
        if title in seen_titles:
            continue
        if title == movie:
            continue
        seen_titles.add(title)
        recommended_movies.append({
            'title': title,
            'overview': movie_data.overview,
            'vote_average': movie_data.vote_average,
            'release_date': movie_data.release_date,
            'genres': movie_data.genres,
            'similarity_score': i[1]
        })
        if len(recommended_movies) >= num_recommendations:
            break
    return recommended_movies

def create_visualizations(movies):
    st.subheader("📊 Data Insights")
    all_genres = []
    for genres in movies['genres']:
        if isinstance(genres, list):
            all_genres.extend(genres)
        else:
            try:
                all_genres.extend([g['name'] for g in ast.literal_eval(genres)])
            except:
                pass
    genre_counts = pd.Series(all_genres).value_counts().head(10)
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Top 10 Genres**")
        fig_genre = px.bar(
            x=genre_counts.values,
            y=genre_counts.index,
            orientation='h',
            title="Most Popular Genres",
            labels={'x': 'Number of Movies', 'y': 'Genre'}
        )
        fig_genre.update_layout(height=400)
        st.plotly_chart(fig_genre, use_container_width=True)
    with col2:
        st.write("**Rating Distribution**")
        fig_rating = px.histogram(
            movies,
            x='vote_average',
            nbins=20,
            title="Movie Rating Distribution",
            labels={'vote_average': 'Rating', 'count': 'Number of Movies'}
        )
        fig_rating.update_layout(height=400)
        st.plotly_chart(fig_rating, use_container_width=True)
    movies['release_year'] = pd.to_datetime(movies['release_date'], errors='coerce').dt.year
    year_counts = movies['release_year'].value_counts().sort_index()
    st.write("**Movies by Release Year**")
    fig_year = px.line(
        x=year_counts.index,
        y=year_counts.values,
        title="Movie Releases Over Time",
        labels={'x': 'Year', 'y': 'Number of Movies'}
    )
    st.plotly_chart(fig_year, use_container_width=True)

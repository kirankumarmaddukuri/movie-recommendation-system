import streamlit as st
import ast
from movie_recommender import load_data, preprocess, create_similarity, recommend, get_movie_poster, create_visualizations

def display_movie_card(movie_data, api_key, poster_cache, is_recommendation=False):
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            poster_url = get_movie_poster(movie_data['title'], api_key, poster_cache)
            if poster_url:
                st.image(poster_url, width=150)
            else:
                st.image("https://via.placeholder.com/150x225/cccccc/666666?text=No+Poster", width=150)
        with col2:
            st.write(f"**{movie_data['title']}**")
            if 'release_date' in movie_data and movie_data['release_date']:
                try:
                    release_year = str(movie_data['release_date'])[:4]
                    st.write(f"📅 {release_year}")
                except:
                    pass
            if 'vote_average' in movie_data and movie_data['vote_average']:
                st.write(f"⭐ {movie_data['vote_average']:.1f}/10")
            if 'genres' in movie_data and movie_data['genres']:
                try:
                    genres = ast.literal_eval(movie_data['genres'])
                    genre_names = [genre['name'] for genre in genres[:3]]
                    st.write(f"🎭 {', '.join(genre_names)}")
                except:
                    pass
            if is_recommendation and 'similarity_score' in movie_data:
                similarity_percent = movie_data['similarity_score'] * 100
                st.write(f"🎯 Similarity: {similarity_percent:.1f}%")
    st.divider()

def main():
    st.set_page_config(
        page_title="Movie Recommendation System",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    if 'poster_cache' not in st.session_state:
        st.session_state.poster_cache = {}
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-bottom: 1rem;
        text-align: center;
    }
    .recommendation-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
    }
    .movie-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #1f77b4;
        max-width: 500px;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">🎬 Movie Recommendation System</h1>', unsafe_allow_html=True)
    with st.sidebar:
        st.header("⚙️ Settings")
        disable_api = st.checkbox("Disable API features (faster loading)", help="Check this to disable movie posters and API calls for faster performance")
        api_key = st.text_input("TMDB API Key (optional)", type="password", help="Enter your TMDB API key to get movie posters and additional details", disabled=disable_api)
        num_recommendations = st.slider("Number of Recommendations", 3, 10, 5)
        st.divider()
        st.write("**About**")
        st.write("This system uses content-based filtering to recommend movies based on genres, cast, crew, and plot similarities.")
        if st.button("Clear API Cache"):
            st.session_state.poster_cache = {}
            st.success("Cache cleared!")
    movies = load_data()
    if movies is None:
        st.error("Failed to load movie data. Please check your CSV files.")
        return
    if st.checkbox("📊 Show Data Insights"):
        create_visualizations(movies)
        st.divider()
    center_col = st.columns([0.15, 0.7, 0.15])[1]
    with center_col:
        st.markdown('<h2 class="sub-header">🎯 Get Movie Recommendations</h2>', unsafe_allow_html=True)
        all_titles = movies['title'].drop_duplicates().sort_values().tolist()
        selected_movie = st.selectbox(
            "Type to search and select a movie:",
            options=all_titles,
            index=0 if all_titles else None,
            help="Start typing a movie name..."
        )
        if st.button("🎬 Get Recommendations", type="primary"):
            if selected_movie:
                with st.spinner("Finding similar movies..."):
                    movies_processed = preprocess(movies)
                    similarity = create_similarity(movies_processed)
                    recommendations = recommend(selected_movie, movies_processed, similarity, num_recommendations)
                if recommendations:
                    st.success(f"Found {len(recommendations)} recommendations!")
                    st.markdown('<div class="recommendation-section">', unsafe_allow_html=True)
                    st.markdown('<h3 class="sub-header">🎯 Recommended Movies</h3>', unsafe_allow_html=True)
                    for i, rec in enumerate(recommendations):
                        st.markdown(f'<div class="movie-card">', unsafe_allow_html=True)
                        st.write(f"**#{i+1} {rec['title']}**")
                        display_movie_card(rec, api_key if not disable_api else None, st.session_state.poster_cache, is_recommendation=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error("No recommendations found. Please try a different movie.")

if __name__ == "__main__":
    main()

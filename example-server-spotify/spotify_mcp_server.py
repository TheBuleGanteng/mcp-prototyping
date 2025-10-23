"""
Spotify MCP Server
Provides tools to search and get information from Spotify
"""

import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize Spotify client
client_credentials_manager = SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Create MCP server
mcp = FastMCP("Spotify")

@mcp.tool()
def search_tracks(query: str, limit: int = 10) -> str:
    """
    Search for tracks on Spotify
    
    Args:
        query: Search query (song name, artist, etc.)
        limit: Maximum number of results (default: 10, max: 50)
    """
    try:
        results = sp.search(q=query, type='track', limit=min(limit, 50))
        if not results or not results.get("tracks") or not results["tracks"]["items"]:
            return f"No results found for track name: '{query}'"
        
        tracks = []
        for item in results['tracks']['items']:
            track_info = {
                'name': item['name'],
                'artist': ', '.join([artist['name'] for artist in item['artists']]),
                'album': item['album']['name'],
                'uri': item['uri'],
                'id': item['id'],
                'preview_url': item.get('preview_url', 'N/A')
            }
            tracks.append(track_info)
        
        output = f"Found {len(tracks)} tracks:\n\n"
        for i, track in enumerate(tracks, 1):
            output += f"{i}. {track['name']} by {track['artist']}\n"
            output += f"   Album: {track['album']}\n"
            output += f"   Track ID: {track['id']}\n"
            output += f"   URI: {track['uri']}\n"
            output += f"   Preview: {track['preview_url']}\n\n"
        
        return output
    
    except SpotifyException as e:
        return f"Spotify API error: {e.msg} (Status: {e.http_status})"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def get_artist_info(artist_name: str) -> str:
    """
    Get detailed information about an artist
    
    Args:
        artist_name: Name of the artist to look up
    """
    try:
        # Search for the artist
        results = sp.search(q=artist_name, type='artist', limit=1)
        
        if not results or not results.get('artists') or not results['artists']['items']:
            return f"No artist found with name: '{artist_name}'"
        
        artist = results['artists']['items'][0]
        artist_id = artist['id']
        
        # Get detailed artist info
        artist_details = sp.artist(artist_id)
        if not artist_details:
            return f"Could not retrieve details for artist: '{artist_name}'"
        
        # Get top tracks
        top_tracks = sp.artist_top_tracks(artist_id)    
        if not top_tracks or not top_tracks.get('tracks'):
            return f"Could not retrieve top tracks for artist: '{artist_name}'"
        
        # Format output
        output = f"Artist: {artist_details['name']}\n"
        output += f"Popularity: {artist_details['popularity']}/100\n"
        output += f"Followers: {artist_details['followers']['total']:,}\n"
        output += f"Genres: {', '.join(artist_details['genres']) if artist_details['genres'] else 'N/A'}\n"
        output += f"Spotify URI: {artist_details['uri']}\n\n"
        
        output += "Top Tracks:\n"
        for i, track in enumerate(top_tracks['tracks'][:5], 1):
            output += f"{i}. {track['name']} - {track['album']['name']}\n"
        
        return output
    
    except SpotifyException as e:
        return f"Spotify API error: {e.msg} (Status: {e.http_status})"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def get_audio_features(track_id: str) -> str:
    """
    Get audio features and analysis for a track (tempo, key, energy, etc.)
    
    Args:
        track_id: Spotify track ID (get this from search_tracks)
    """
    try:
        # Get audio features
        features_response = sp.audio_features(track_id)

        if not features_response or not features_response[0]:
            return f"No audio features found for track ID: '{track_id}'"

        
        # Get basic track info
        features = features_response[0]
        track = sp.track(track_id)
        if not track:
            return f"Could not retrieve track information for ID: '{track_id}'"
        
        output = f"Audio Features for: {track['name']} by {track['artists'][0]['name']}\n\n"
        output += f"Tempo: {features['tempo']:.1f} BPM\n"
        output += f"Key: {features['key']} (0=C, 1=C#, 2=D, etc.)\n"
        output += f"Mode: {'Major' if features['mode'] == 1 else 'Minor'}\n"
        output += f"Time Signature: {features['time_signature']}/4\n"
        output += f"Duration: {features['duration_ms'] / 1000:.1f} seconds\n\n"
        
        output += "Musical Characteristics (0.0 to 1.0):\n"
        output += f"  Danceability: {features['danceability']:.2f}\n"
        output += f"  Energy: {features['energy']:.2f}\n"
        output += f"  Speechiness: {features['speechiness']:.2f}\n"
        output += f"  Acousticness: {features['acousticness']:.2f}\n"
        output += f"  Instrumentalness: {features['instrumentalness']:.2f}\n"
        output += f"  Liveness: {features['liveness']:.2f}\n"
        output += f"  Valence (positivity): {features['valence']:.2f}\n"
        output += f"  Loudness: {features['loudness']:.1f} dB\n"
        
        return output
    
    except SpotifyException as e:
        return f"Spotify API error: {e.msg} (Status: {e.http_status})"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def get_recommendations(seed_track_ids: str, limit: int = 10) -> str:
    """
    Get track recommendations based on seed tracks
    
    Args:
        seed_track_ids: Comma-separated Spotify track IDs (up to 5)
        limit: Number of recommendations (default: 10, max: 100)
    """
    try:
        # Parse track IDs
        track_ids = [tid.strip() for tid in seed_track_ids.split(',')][:5]
        
        if not track_ids:
            return "Please provide at least one track ID"
        
        # Get recommendations
        results = sp.recommendations(seed_tracks=track_ids, limit=min(limit, 100))
        
        if not results or not results['tracks']:
            return "No recommendations found for the given tracks"
        
        output = f"Recommendations based on {len(track_ids)} seed track(s):\n\n"
        
        for i, track in enumerate(results['tracks'], 1):
            output += f"{i}. {track['name']} by {', '.join([artist['name'] for artist in track['artists']])}\n"
            output += f"   Album: {track['album']['name']}\n"
            output += f"   Track ID: {track['id']}\n"
            output += f"   Popularity: {track['popularity']}/100\n\n"
        
        return output
    
    except SpotifyException as e:
        return f"Spotify API error: {e.msg} (Status: {e.http_status})"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


if __name__ == "__main__":
    mcp.run()
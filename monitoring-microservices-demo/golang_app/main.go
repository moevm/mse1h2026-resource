package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
	"sync"
)

type album struct {
	ID     string  `json:"id"`
	Title  string  `json:"title"`
	Artist string  `json:"artist"`
	Price  float64 `json:"price"`
	Genre  string  `json:"genre"`
	Year   int     `json:"year"`
}

type category struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Slug string `json:"slug"`
}

var (
	albums = []album{
		{ID: "1", Title: "Blue Train", Artist: "John Coltrane", Price: 56.99, Genre: "Jazz", Year: 1958},
		{ID: "2", Title: "Jeru", Artist: "Gerry Mulligan", Price: 17.99, Genre: "Jazz", Year: 1962},
		{ID: "3", Title: "Sarah Vaughan and Clifford Brown", Artist: "Sarah Vaughan", Price: 39.99, Genre: "Jazz", Year: 1954},
		{ID: "4", Title: "Kind of Blue", Artist: "Miles Davis", Price: 45.99, Genre: "Jazz", Year: 1959},
		{ID: "5", Title: "A Love Supreme", Artist: "John Coltrane", Price: 32.99, Genre: "Jazz", Year: 1965},
		{ID: "6", Title: "Abbey Road", Artist: "The Beatles", Price: 29.99, Genre: "Rock", Year: 1969},
		{ID: "7", Title: "Dark Side of the Moon", Artist: "Pink Floyd", Price: 34.99, Genre: "Rock", Year: 1973},
		{ID: "8", Title: "Rumours", Artist: "Fleetwood Mac", Price: 27.99, Genre: "Rock", Year: 1977},
	}

	categories = []category{
		{ID: "1", Name: "Jazz", Slug: "jazz"},
		{ID: "2", Name: "Rock", Slug: "rock"},
		{ID: "3", Name: "Classical", Slug: "classical"},
		{ID: "4", Name: "Electronic", Slug: "electronic"},
		{ID: "5", Name: "Hip Hop", Slug: "hip-hop"},
	}

	nextID   = 9
	nextIDMu sync.Mutex

	serviceName = "product-service"
	serviceVer  = "2.1.0"
	pathAlbums  = "/albums"
)

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, 200, map[string]string{"status": "healthy", "service": serviceName})
	})

	mux.HandleFunc(pathAlbums, func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			genre := r.URL.Query().Get("genre")
			if genre != "" {
				var filtered []album
				for _, a := range albums {
					if strings.EqualFold(a.Genre, genre) {
						filtered = append(filtered, a)
					}
				}
				writeJSON(w, 200, filtered)
				return
			}
			writeJSON(w, 200, albums)
			log.Printf("GET /albums -> %d items", len(albums))

		case http.MethodPost:
			var a album
			if err := json.NewDecoder(r.Body).Decode(&a); err != nil {
				writeJSON(w, 400, map[string]string{"error": "invalid json"})
				return
			}
			nextIDMu.Lock()
			a.ID = strconv.Itoa(nextID)
			nextID++
			nextIDMu.Unlock()
			albums = append(albums, a)
			writeJSON(w, 201, a)
			log.Printf("POST /albums -> created id=%s", a.ID)

		default:
			writeJSON(w, 405, map[string]string{"error": "method not allowed"})
		}
	})

	mux.HandleFunc("/albums/", func(w http.ResponseWriter, r *http.Request) {
		id := strings.TrimPrefix(r.URL.Path, "/albums/")
		if id == "" {
			http.Redirect(w, r, pathAlbums, http.StatusMovedPermanently)
			return
		}

		switch r.Method {
		case http.MethodGet:
			for _, a := range albums {
				if a.ID == id {
					writeJSON(w, 200, a)
					return
				}
			}
			writeJSON(w, 404, map[string]string{"error": "album not found"})

		case http.MethodDelete:
			for i, a := range albums {
				if a.ID == id {
					albums = append(albums[:i], albums[i+1:]...)
					writeJSON(w, 200, map[string]string{"deleted": id})
					return
				}
			}
			writeJSON(w, 404, map[string]string{"error": "album not found"})

		default:
			writeJSON(w, 405, map[string]string{"error": "method not allowed"})
		}
	})

	mux.HandleFunc("/categories", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, 200, categories)
	})

	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, 200, map[string]interface{}{
			"total_albums":     len(albums),
			"total_categories": len(categories),
			"service":          serviceName,
			"version":          "2.1.0",
		})
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			writeJSON(w, 404, map[string]string{"error": "not found"})
			return
		}
		writeJSON(w, 200, map[string]interface{}{
			"service":   serviceName,
			"version":   "2.1.0",
			"endpoints": []string{pathAlbums, "/albums/{id}", "/categories", "/stats", "/health"},
		})
	})

	port := ":8002"
	log.Printf("Product Service starting on port %s", port)
	log.Fatal(http.ListenAndServe(port, mux))
}

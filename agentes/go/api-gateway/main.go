package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/dgrijalva/jwt-go"
	"github.com/go-redis/redis/v8"
	"github.com/gorilla/mux"
	"golang.org/x/crypto/bcrypt"
	"google.golang.org/grpc"
	
	pb "github.com/jlpy/agentes/proto"
)

var (
	jwtSecret     = []byte(os.Getenv("JWT_SECRET"))
	redisClient   *redis.Client
	grpcClient    pb.AgentFrameworkClient
)

// Claims estructura para JWT
type Claims struct {
	Username string `json:"username"`
	Role     string `json:"role"`
	jwt.StandardClaims
}

// User estructura
type User struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
	Password string `json:"-"`
	Role     string `json:"role"`
}

// LoginRequest estructura
type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// ProcessRequest estructura
type ProcessRequest struct {
	Requirement              string            `json:"requirement"`
	Context                  map[string]string `json:"context"`
	EnablePeerReview         bool              `json:"enable_peer_review"`
	EnableExecutableFeedback bool              `json:"enable_executable_feedback"`
}

func init() {
	// Inicializar Redis
	redisHost := os.Getenv("REDIS_HOST")
	if redisHost == "" {
		redisHost = "localhost:6379"
	}
	
	redisClient = redis.NewClient(&redis.Options{
		Addr: redisHost,
	})

	// Inicializar gRPC client
	grpcServer := os.Getenv("GRPC_SERVER")
	if grpcServer == "" {
		grpcServer = "localhost:50051"
	}

	conn, err := grpc.Dial(grpcServer, grpc.WithInsecure())
	if err != nil {
		log.Fatalf("Failed to connect to gRPC server: %v", err)
	}

	grpcClient = pb.NewAgentFrameworkClient(conn)
}

// Middleware de autenticación
func authMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			http.Error(w, "Missing authorization header", http.StatusUnauthorized)
			return
		}

		tokenString := strings.Replace(authHeader, "Bearer ", "", 1)

		claims := &Claims{}
		token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
			return jwtSecret, nil
		})

		if err != nil || !token.Valid {
			http.Error(w, "Invalid token", http.StatusUnauthorized)
			return
		}

		// Agregar claims al contexto
		ctx := context.WithValue(r.Context(), "claims", claims)
		next.ServeHTTP(w, r.WithContext(ctx))
	}
}

// Middleware de rate limiting
func rateLimitMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx := context.Background()
		
		// Obtener IP del cliente
		ip := r.RemoteAddr
		key := fmt.Sprintf("rate_limit:%s", ip)

		// Incrementar contador
		count, err := redisClient.Incr(ctx, key).Result()
		if err != nil {
			log.Printf("Redis error: %v", err)
			next.ServeHTTP(w, r)
			return
		}

		// Establecer expiración si es la primera request
		if count == 1 {
			redisClient.Expire(ctx, key, time.Minute)
		}

		// Límite: 60 requests por minuto
		if count > 60 {
			http.Error(w, "Rate limit exceeded", http.StatusTooManyRequests)
			return
		}

		// Agregar headers de rate limit
		w.Header().Set("X-RateLimit-Limit", "60")
		w.Header().Set("X-RateLimit-Remaining", fmt.Sprintf("%d", 60-count))

		next.ServeHTTP(w, r)
	}
}

// Handler de login
func loginHandler(w http.ResponseWriter, r *http.Request) {
	var req LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// TODO: Verificar usuario en base de datos
	// Por ahora, usuario de prueba
	if req.Username != "admin" || req.Password != "admin" {
		http.Error(w, "Invalid credentials", http.StatusUnauthorized)
		return
	}

	// Crear token JWT
	expirationTime := time.Now().Add(24 * time.Hour)
	claims := &Claims{
		Username: req.Username,
		Role:     "admin",
		StandardClaims: jwt.StandardClaims{
			ExpiresAt: expirationTime.Unix(),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString(jwtSecret)
	if err != nil {
		http.Error(w, "Error generating token", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]string{
		"token": tokenString,
		"expires_at": expirationTime.Format(time.RFC3339),
	})
}

// Handler de procesamiento
func processHandler(w http.ResponseWriter, r *http.Request) {
	var req ProcessRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// Llamar a gRPC
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	result, err := grpcClient.ProcessRequirement(ctx, &pb.RequirementRequest{
		Requirement:              req.Requirement,
		Context:                  req.Context,
		EnablePeerReview:         req.EnablePeerReview,
		EnableExecutableFeedback: req.EnableExecutableFeedback,
	})

	if err != nil {
		http.Error(w, fmt.Sprintf("Error processing: %v", err), http.StatusInternalServerError)
		return
	}

	// Convertir a JSON y retornar
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

// Handler de estado de tarea
func taskStatusHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	taskID := vars["id"]

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	status, err := grpcClient.GetTaskStatus(ctx, &pb.TaskStatusRequest{
		TaskId: taskID,
	})

	if err != nil {
		http.Error(w, fmt.Sprintf("Error getting status: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// Handler de health check
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"timestamp": time.Now().Format(time.RFC3339),
	})
}

// Handler de métricas (Prometheus)
func metricsHandler(w http.ResponseWriter, r *http.Request) {
	// TODO: Implementar métricas Prometheus
	w.Write([]byte("# Metrics\n"))
}

func main() {
	r := mux.NewRouter()

	// Rutas públicas
	r.HandleFunc("/health", healthHandler).Methods("GET")
	r.HandleFunc("/metrics", metricsHandler).Methods("GET")
	r.HandleFunc("/api/v1/login", loginHandler).Methods("POST")

	// Rutas protegidas
	r.HandleFunc("/api/v1/process", 
		rateLimitMiddleware(authMiddleware(processHandler))).Methods("POST")
	r.HandleFunc("/api/v1/tasks/{id}", 
		authMiddleware(taskStatusHandler)).Methods("GET")

	// CORS
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
			
			if r.Method == "OPTIONS" {
				w.WriteHeader(http.StatusOK)
				return
			}
			
			next.ServeHTTP(w, r)
		})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("API Gateway starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}

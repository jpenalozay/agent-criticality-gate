package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	
	// Importar proto generado
	// protoc --go_out=. --go_opt=paths=source_relative --go-grpc_out=. --go-grpc_opt=paths=source_relative proto/services.proto
	pb "github.com/jlpy/agentes/proto"
)

// Client es el cliente gRPC para el framework
type Client struct {
	conn   *grpc.ClientConn
	client pb.AgentFrameworkClient
}

// NewClient crea un nuevo cliente gRPC
func NewClient(address string) (*Client, error) {
	conn, err := grpc.Dial(
		address,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
		grpc.WithTimeout(10*time.Second),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect: %v", err)
	}

	client := pb.NewAgentFrameworkClient(conn)

	return &Client{
		conn:   conn,
		client: client,
	}, nil
}

// Close cierra la conexión
func (c *Client) Close() error {
	return c.conn.Close()
}

// ProcessRequirement procesa un requerimiento completo
func (c *Client) ProcessRequirement(
	ctx context.Context,
	requirement string,
	context map[string]string,
	enablePeerReview bool,
	enableExecutableFeedback bool,
) (*pb.ProcessResult, error) {
	req := &pb.RequirementRequest{
		Requirement:              requirement,
		Context:                  context,
		EnablePeerReview:         enablePeerReview,
		EnableExecutableFeedback: enableExecutableFeedback,
	}

	result, err := c.client.ProcessRequirement(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("ProcessRequirement failed: %v", err)
	}

	return result, nil
}

// GetTaskStatus obtiene el estado de una tarea
func (c *Client) GetTaskStatus(ctx context.Context, taskID string) (*pb.TaskStatus, error) {
	req := &pb.TaskStatusRequest{
		TaskId: taskID,
	}

	status, err := c.client.GetTaskStatus(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("GetTaskStatus failed: %v", err)
	}

	return status, nil
}

// ListTasks lista tareas recientes
func (c *Client) ListTasks(ctx context.Context, limit, offset int32) (*pb.TaskList, error) {
	req := &pb.ListTasksRequest{
		Limit:  limit,
		Offset: offset,
	}

	tasks, err := c.client.ListTasks(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("ListTasks failed: %v", err)
	}

	return tasks, nil
}

// GetAuditLogs obtiene logs de auditoría
func (c *Client) GetAuditLogs(ctx context.Context, taskID string, limit int32) (*pb.AuditLogs, error) {
	req := &pb.AuditLogsRequest{
		TaskId: taskID,
		Limit:  limit,
	}

	logs, err := c.client.GetAuditLogs(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("GetAuditLogs failed: %v", err)
	}

	return logs, nil
}

// PrintResult imprime el resultado de forma legible
func PrintResult(result *pb.ProcessResult) {
	fmt.Println("="*70)
	fmt.Println("RESULTADO DEL FRAMEWORK")
	fmt.Println("="*70)
	fmt.Printf("Task ID: %s\n", result.TaskId)
	fmt.Printf("Status: %s\n", result.Status)
	fmt.Printf("Time: %dms\n", result.TotalTimeMs)

	if result.Summary != nil {
		fmt.Println("\nRESUMEN:")
		
		if result.Summary.Architecture != nil {
			fmt.Printf("  Arquitectura: %s (%d componentes)\n",
				result.Summary.Architecture.Name,
				result.Summary.Architecture.Components)
		}

		if result.Summary.Risk != nil {
			fmt.Printf("  Riesgo: %.1f (%s) - %s\n",
				result.Summary.Risk.Score,
				result.Summary.Risk.Level,
				result.Summary.Risk.Decision)
		}

		if result.Summary.Testing != nil {
			fmt.Printf("  Tests: %d/%d passed (%.0f%% coverage)\n",
				result.Summary.Testing.TestsPassed,
				result.Summary.Testing.TestsDesigned,
				result.Summary.Testing.Coverage*100)
		}

		if result.Summary.Quality != nil {
			fmt.Printf("  Calidad: %.1f/100 (%d issues)\n",
				result.Summary.Quality.Score,
				result.Summary.Quality.Issues)
		}
	}

	if result.Error != "" {
		fmt.Printf("\nError: %s\n", result.Error)
	}

	fmt.Println("="*70)
}

func main() {
	// Ejemplo de uso
	log.Println("Conectando al framework...")

	client, err := NewClient("localhost:50051")
	if err != nil {
		log.Fatalf("Error conectando: %v", err)
	}
	defer client.Close()

	log.Println("✓ Conectado al framework")

	// Procesar requerimiento
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	log.Println("\nProcesando requerimiento...")
	result, err := client.ProcessRequirement(
		ctx,
		"Crear una calculadora simple con operaciones básicas",
		nil,
		false, // peer review
		false, // executable feedback
	)

	if err != nil {
		log.Fatalf("Error procesando: %v", err)
	}

	PrintResult(result)

	// Obtener audit logs
	log.Println("\nObteniendo audit logs...")
	logs, err := client.GetAuditLogs(ctx, result.TaskId, 10)
	if err != nil {
		log.Printf("Error obteniendo logs: %v", err)
	} else {
		fmt.Printf("\n📝 Audit Logs: %d eventos\n", logs.Total)
		for i, event := range logs.Events {
			if i < 5 { // Mostrar solo primeros 5
				fmt.Printf("  %d. %s: %s.%s\n",
					i+1,
					event.Timestamp,
					event.Actor,
					event.Action)
			}
		}
	}

	log.Println("\n✓ Completado")
}

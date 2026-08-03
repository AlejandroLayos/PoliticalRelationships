package store

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
)

// Los tests de este fichero necesitan un Postgres real con PostGIS. Se salta
// si no hay DSN, para que `go test ./...` siga funcionando sin base de datos.
//
//	SINAPSIS_TEST_POSTGRES_DSN=postgres://postgres@127.0.0.1:5433/sinapsis_test?sslmode=disable go test ./internal/store/
func nuevoStoreDePrueba(t *testing.T) *Store {
	t.Helper()

	dsn := os.Getenv("SINAPSIS_TEST_POSTGRES_DSN")
	if dsn == "" {
		t.Skip("SINAPSIS_TEST_POSTGRES_DSN sin definir; se salta el test de integración")
	}

	ctx := context.Background()
	st, err := Open(ctx, dsn)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(st.Close)

	if err := st.Ping(ctx); err != nil {
		t.Fatalf("Ping: %v", err)
	}
	aplicarMigraciones(t, st)
	limpiar(t, st)
	return st
}

// aplicarMigraciones deja el esquema al día. Aplica los .up.sql en orden.
func aplicarMigraciones(t *testing.T, st *Store) {
	t.Helper()
	ctx := context.Background()

	// ¿Ya está el esquema? Comprobamos la última pieza que añade 0002.
	var existe bool
	err := st.pool.QueryRow(ctx, `
		SELECT EXISTS (
			SELECT 1 FROM information_schema.columns
			WHERE table_name = 'entities' AND column_name = 'dedupe_key'
		)`).Scan(&existe)
	if err == nil && existe {
		return
	}

	patrones, err := filepath.Glob(filepath.Join("..", "..", "migrations", "*.up.sql"))
	if err != nil || len(patrones) == 0 {
		t.Fatalf("no encuentro migraciones: %v", err)
	}
	for _, ruta := range patrones {
		sql, err := os.ReadFile(ruta)
		if err != nil {
			t.Fatalf("leyendo %s: %v", ruta, err)
		}
		if _, err := st.pool.Exec(ctx, string(sql)); err != nil {
			t.Fatalf("aplicando %s: %v", filepath.Base(ruta), err)
		}
	}
}

// limpiar vacía las tablas entre tests. TRUNCATE no dispara el trigger de
// inmutabilidad de raw_documents, que sólo vigila UPDATE.
func limpiar(t *testing.T, st *Store) {
	t.Helper()
	_, err := st.pool.Exec(context.Background(),
		`TRUNCATE provenance, entity_resolution_decisions, review_queue,
		          relationships, entities, raw_documents, sources CASCADE`)
	if err != nil {
		t.Fatalf("limpiando tablas: %v", err)
	}
}

func hash(b []byte) string {
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}

func sembrarFuente(t *testing.T, st *Store) {
	t.Helper()
	err := st.UpsertSource(context.Background(), Source{
		ID:      "bdns",
		Name:    "Base de Datos Nacional de Subvenciones",
		URL:     "https://www.infosubvenciones.es",
		License: "Reutilización libre",
	})
	if err != nil {
		t.Fatalf("UpsertSource: %v", err)
	}
}

func docDePrueba(contenido []byte) RawDocument {
	return RawDocument{
		SourceID:    "bdns",
		URL:         "https://www.infosubvenciones.es/api/convocatorias/busqueda?page=0",
		Content:     contenido,
		ContentHash: hash(contenido),
		MediaType:   "application/json",
		RetrievedAt: time.Now().UTC().Truncate(time.Microsecond),
		Metadata:    map[string]any{"pagina": float64(0)},
	}
}

// --- fuentes --------------------------------------------------------------

func TestUpsertSourceEsIdempotente(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()

	src := Source{ID: "bdns", Name: "BDNS", URL: "https://ejemplo.test"}
	for range 3 {
		if err := st.UpsertSource(ctx, src); err != nil {
			t.Fatalf("UpsertSource: %v", err)
		}
	}

	var n int
	if err := st.pool.QueryRow(ctx, `SELECT count(*) FROM sources`).Scan(&n); err != nil {
		t.Fatal(err)
	}
	if n != 1 {
		t.Errorf("hay %d fuentes tras 3 upserts, quería 1", n)
	}
}

func TestUpsertSourceActualizaCampos(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()

	if err := st.UpsertSource(ctx, Source{ID: "bdns", Name: "viejo"}); err != nil {
		t.Fatal(err)
	}
	if err := st.UpsertSource(ctx, Source{ID: "bdns", Name: "nuevo"}); err != nil {
		t.Fatal(err)
	}

	var nombre string
	if err := st.pool.QueryRow(ctx, `SELECT name FROM sources WHERE id='bdns'`).Scan(&nombre); err != nil {
		t.Fatal(err)
	}
	if nombre != "nuevo" {
		t.Errorf("name = %q, quería \"nuevo\"", nombre)
	}
}

// --- documentos crudos ----------------------------------------------------

func TestUpsertRawDocumentIdempotentePorHash(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	sembrarFuente(t, st)

	doc := docDePrueba([]byte(`{"convocatorias":[]}`))

	id1, creado1, err := st.UpsertRawDocument(ctx, doc)
	if err != nil {
		t.Fatalf("primer upsert: %v", err)
	}
	if !creado1 {
		t.Error("el primer upsert debería reportar creado=true")
	}

	// Reejecución: mismos bytes, distinta hora de descarga y metadatos.
	doc2 := doc
	doc2.RetrievedAt = doc.RetrievedAt.Add(24 * time.Hour)
	doc2.Metadata = map[string]any{"pagina": float64(99)}

	id2, creado2, err := st.UpsertRawDocument(ctx, doc2)
	if err != nil {
		t.Fatalf("segundo upsert: %v", err)
	}
	if creado2 {
		t.Error("el segundo upsert debería reportar creado=false")
	}
	if id1 != id2 {
		t.Errorf("ids distintos (%s vs %s); la reejecución duplicó", id1, id2)
	}

	n, err := st.CountRawDocuments(ctx, "bdns")
	if err != nil {
		t.Fatal(err)
	}
	if n != 1 {
		t.Errorf("hay %d documentos, quería 1", n)
	}
}

func TestUpsertRawDocumentDistintoHashCreaFila(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	sembrarFuente(t, st)

	if _, _, err := st.UpsertRawDocument(ctx, docDePrueba([]byte(`{"a":1}`))); err != nil {
		t.Fatal(err)
	}
	if _, _, err := st.UpsertRawDocument(ctx, docDePrueba([]byte(`{"a":2}`))); err != nil {
		t.Fatal(err)
	}

	n, _ := st.CountRawDocuments(ctx, "bdns")
	if n != 2 {
		t.Errorf("hay %d documentos, quería 2", n)
	}
}

func TestMismosBytesDeFuentesDistintasNoColapsan(t *testing.T) {
	// El UNIQUE va por (source_id, content_hash): dos fuentes pueden servir
	// bytes idénticos legítimamente y cada una conserva su procedencia.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	sembrarFuente(t, st)
	if err := st.UpsertSource(ctx, Source{ID: "placsp", Name: "PLACSP"}); err != nil {
		t.Fatal(err)
	}

	contenido := []byte(`{"identico":true}`)
	docA := docDePrueba(contenido)
	docB := docDePrueba(contenido)
	docB.SourceID = "placsp"

	idA, creadoA, err := st.UpsertRawDocument(ctx, docA)
	if err != nil {
		t.Fatal(err)
	}
	idB, creadoB, err := st.UpsertRawDocument(ctx, docB)
	if err != nil {
		t.Fatal(err)
	}

	if !creadoA || !creadoB {
		t.Error("ambos documentos deberían crearse")
	}
	if idA == idB {
		t.Error("los documentos de fuentes distintas colapsaron en una fila")
	}
}

func TestRawDocumentEsInmutable(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	sembrarFuente(t, st)

	id, _, err := st.UpsertRawDocument(ctx, docDePrueba([]byte(`{"x":1}`)))
	if err != nil {
		t.Fatal(err)
	}

	_, err = st.pool.Exec(ctx, `UPDATE raw_documents SET url = 'otra' WHERE id = $1`, id)
	if err == nil {
		t.Fatal("el UPDATE sobre raw_documents debería haber fallado")
	}
	if !strings.Contains(err.Error(), "inmutable") {
		t.Errorf("error = %v; esperaba el del trigger de inmutabilidad", err)
	}
}

// --- entidades ------------------------------------------------------------

func TestUpsertEntityIdempotente(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()

	e := Entity{
		FtmSchema: "Company",
		Caption:   "Construcciones García SL",
		NIF:       "B12345678",
		DedupeKey: "nif:B12345678",
		Country:   "es",
	}

	id1, err := st.UpsertEntity(ctx, e)
	if err != nil {
		t.Fatalf("primer upsert: %v", err)
	}
	id2, err := st.UpsertEntity(ctx, e)
	if err != nil {
		t.Fatalf("segundo upsert: %v", err)
	}
	if id1 != id2 {
		t.Errorf("ids distintos (%s vs %s); la entidad se duplicó", id1, id2)
	}
}

func TestUpsertEntityFusionaPropiedades(t *testing.T) {
	// Dos fuentes aportan campos distintos de la misma empresa. La segunda no
	// debe borrar lo que trajo la primera.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()

	base := Entity{
		FtmSchema: "Company", Caption: "Construcciones García SL",
		NIF: "B12345678", DedupeKey: "nif:B12345678",
	}
	base.Properties = map[string]any{"cnae": "4121"}
	if _, err := st.UpsertEntity(ctx, base); err != nil {
		t.Fatal(err)
	}

	base.Properties = map[string]any{"domicilio": "Madrid"}
	if _, err := st.UpsertEntity(ctx, base); err != nil {
		t.Fatal(err)
	}

	got, err := st.EntityByDedupeKey(ctx, "nif:B12345678")
	if err != nil {
		t.Fatal(err)
	}
	if got.Properties["cnae"] != "4121" {
		t.Errorf("se perdió cnae de la primera fuente: %v", got.Properties)
	}
	if got.Properties["domicilio"] != "Madrid" {
		t.Errorf("no se añadió domicilio de la segunda fuente: %v", got.Properties)
	}
}

func TestUpsertEntitySinDedupeKeyFalla(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	_, err := st.UpsertEntity(context.Background(), Entity{FtmSchema: "Company", Caption: "X"})
	if err == nil {
		t.Fatal("una entidad sin DedupeKey debería ser rechazada")
	}
}

func TestUpsertEntityRechazaEsquemaQueEsArista(t *testing.T) {
	// 'Payment' es una arista en FollowTheMoney; el CHECK del esquema lo para.
	st := nuevoStoreDePrueba(t)
	_, err := st.UpsertEntity(context.Background(), Entity{
		FtmSchema: "Payment", Caption: "X", DedupeKey: "k",
	})
	if err == nil {
		t.Fatal("debería rechazar un esquema de arista en entities")
	}
}

// --- aristas --------------------------------------------------------------

func crearDosEntidades(t *testing.T, st *Store) (organismo, empresa uuid.UUID) {
	t.Helper()
	ctx := context.Background()

	var err error
	organismo, err = st.UpsertEntity(ctx, Entity{
		FtmSchema: "PublicBody", Caption: "Ministerio de Hacienda",
		NIF: "S2800000A", DedupeKey: "nif:S2800000A",
	})
	if err != nil {
		t.Fatal(err)
	}
	empresa, err = st.UpsertEntity(ctx, Entity{
		FtmSchema: "Company", Caption: "Construcciones García SL",
		NIF: "B12345678", DedupeKey: "nif:B12345678",
	})
	if err != nil {
		t.Fatal(err)
	}
	return organismo, empresa
}

func TestUpsertRelationshipIdempotente(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	organismo, empresa := crearDosEntidades(t, st)

	inicio := time.Date(2025, 3, 1, 0, 0, 0, 0, time.UTC)
	r := Relationship{
		FtmSchema:      "Payment",
		SourceEntityID: organismo,
		TargetEntityID: empresa,
		Amount:         "50000.00",
		Currency:       "EUR",
		StartDate:      &inicio,
		Confidence:     0.95,
		Status:         StatusAsserted,
		DedupeKey:      "bdns:concesion:987654",
	}

	id1, err := st.UpsertRelationship(ctx, r)
	if err != nil {
		t.Fatalf("primer upsert: %v", err)
	}
	id2, err := st.UpsertRelationship(ctx, r)
	if err != nil {
		t.Fatalf("segundo upsert: %v", err)
	}
	if id1 != id2 {
		t.Errorf("ids distintos (%s vs %s); la arista se duplicó", id1, id2)
	}

	var n int
	if err := st.pool.QueryRow(ctx, `SELECT count(*) FROM relationships`).Scan(&n); err != nil {
		t.Fatal(err)
	}
	if n != 1 {
		t.Errorf("hay %d aristas, quería 1", n)
	}
}

func TestImporteConservaLosDecimales(t *testing.T) {
	// El importe es el dato que da sentido al proyecto: si se redondea, el
	// resto da igual.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	organismo, empresa := crearDosEntidades(t, st)

	id, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: organismo, TargetEntityID: empresa,
		Amount: "1234567890123.45", Currency: "EUR",
		Confidence: 1, DedupeKey: "k",
	})
	if err != nil {
		t.Fatal(err)
	}

	var got string
	if err := st.pool.QueryRow(ctx,
		`SELECT amount::text FROM relationships WHERE id = $1`, id).Scan(&got); err != nil {
		t.Fatal(err)
	}
	if got != "1234567890123.45" {
		t.Errorf("amount = %q, quería \"1234567890123.45\"", got)
	}
}

func TestRelationshipRechazaConfianzaFueraDeRango(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	organismo, empresa := crearDosEntidades(t, st)

	_, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: organismo, TargetEntityID: empresa,
		Confidence: 1.5, DedupeKey: "k",
	})
	if err == nil {
		t.Fatal("confidence = 1.5 debería ser rechazado")
	}
}

func TestRelationshipRechazaImporteSinMoneda(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	organismo, empresa := crearDosEntidades(t, st)

	_, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: organismo, TargetEntityID: empresa,
		Amount: "1000", Confidence: 0.9, DedupeKey: "k",
	})
	if err == nil {
		t.Fatal("un importe sin moneda debería ser rechazado")
	}
}

func TestRelationshipStatusPorDefectoEsAsserted(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	organismo, empresa := crearDosEntidades(t, st)

	id, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: organismo, TargetEntityID: empresa,
		Confidence: 0.9, DedupeKey: "k",
	})
	if err != nil {
		t.Fatal(err)
	}

	var status string
	if err := st.pool.QueryRow(ctx,
		`SELECT status FROM relationships WHERE id = $1`, id).Scan(&status); err != nil {
		t.Fatal(err)
	}
	if status != StatusAsserted {
		t.Errorf("status = %q, quería %q", status, StatusAsserted)
	}
}

// --- procedencia ----------------------------------------------------------

func TestCicloCompletoConProcedencia(t *testing.T) {
	// El criterio de aceptación de la fase 1: insertar crudo, derivar entidad
	// y arista, y poder volver del hecho al documento original.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	sembrarFuente(t, st)

	doc := docDePrueba([]byte(`{"concesion":987654,"importe":50000}`))
	docID, creado, err := st.UpsertRawDocument(ctx, doc)
	if err != nil || !creado {
		t.Fatalf("upsert de crudo: %v (creado=%v)", err, creado)
	}

	organismo, empresa := crearDosEntidades(t, st)

	relID, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: organismo, TargetEntityID: empresa,
		Amount: "50000.00", Currency: "EUR", Confidence: 0.95,
		DedupeKey: "bdns:concesion:987654",
	})
	if err != nil {
		t.Fatal(err)
	}

	err = st.AddProvenance(ctx, Provenance{
		RawDocumentID: docID, RelationshipID: relID,
		ExtractorVersion: "bdns/1", Excerpt: `"importe":50000`,
	})
	if err != nil {
		t.Fatal(err)
	}
	err = st.AddProvenance(ctx, Provenance{
		RawDocumentID: docID, EntityID: empresa,
		ExtractorVersion: "bdns/1",
	})
	if err != nil {
		t.Fatal(err)
	}

	refs, err := st.ProvenanceForRelationship(ctx, relID)
	if err != nil {
		t.Fatal(err)
	}
	if len(refs) != 1 {
		t.Fatalf("hay %d procedencias para la arista, quería 1", len(refs))
	}
	if refs[0].ContentHash != doc.ContentHash {
		t.Errorf("hash = %q, quería %q", refs[0].ContentHash, doc.ContentHash)
	}
	if refs[0].URL != doc.URL {
		t.Errorf("url = %q, quería %q", refs[0].URL, doc.URL)
	}
	if refs[0].Excerpt != `"importe":50000` {
		t.Errorf("excerpt = %q", refs[0].Excerpt)
	}

	refsEnt, err := st.ProvenanceForEntity(ctx, empresa)
	if err != nil {
		t.Fatal(err)
	}
	if len(refsEnt) != 1 {
		t.Errorf("hay %d procedencias para la entidad, quería 1", len(refsEnt))
	}
}

func TestAddProvenanceEsIdempotente(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	sembrarFuente(t, st)

	docID, _, err := st.UpsertRawDocument(ctx, docDePrueba([]byte(`{"x":1}`)))
	if err != nil {
		t.Fatal(err)
	}
	organismo, empresa := crearDosEntidades(t, st)
	relID, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: organismo, TargetEntityID: empresa,
		Confidence: 0.9, DedupeKey: "k",
	})
	if err != nil {
		t.Fatal(err)
	}

	p := Provenance{RawDocumentID: docID, RelationshipID: relID, ExtractorVersion: "bdns/1"}
	for range 3 {
		if err := st.AddProvenance(ctx, p); err != nil {
			t.Fatalf("AddProvenance: %v", err)
		}
	}

	refs, err := st.ProvenanceForRelationship(ctx, relID)
	if err != nil {
		t.Fatal(err)
	}
	if len(refs) != 1 {
		t.Errorf("hay %d procedencias tras 3 inserciones, quería 1", len(refs))
	}
}

func TestAddProvenanceSinDocumentoFalla(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	err := st.AddProvenance(context.Background(), Provenance{
		EntityID: uuid.New(), ExtractorVersion: "v1",
	})
	if err == nil {
		t.Fatal("procedencia sin documento crudo debería fallar")
	}
}

func TestAddProvenanceConDosSujetosFalla(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	err := st.AddProvenance(context.Background(), Provenance{
		RawDocumentID: uuid.New(), EntityID: uuid.New(), RelationshipID: uuid.New(),
		ExtractorVersion: "v1",
	})
	if err == nil {
		t.Fatal("procedencia con entidad y arista a la vez debería fallar")
	}
}

// --- reejecución completa -------------------------------------------------

func TestIngestaCompletaReejecutadaNoDuplica(t *testing.T) {
	// Simula ejecutar el mismo conector dos veces seguidas.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	sembrarFuente(t, st)

	ingesta := func() {
		docID, _, err := st.UpsertRawDocument(ctx, docDePrueba([]byte(`{"concesion":1}`)))
		if err != nil {
			t.Fatal(err)
		}
		organismo, empresa := crearDosEntidades(t, st)
		relID, err := st.UpsertRelationship(ctx, Relationship{
			FtmSchema: "Payment", SourceEntityID: organismo, TargetEntityID: empresa,
			Amount: "1000.00", Currency: "EUR", Confidence: 0.95,
			DedupeKey: "bdns:concesion:1",
		})
		if err != nil {
			t.Fatal(err)
		}
		if err := st.AddProvenance(ctx, Provenance{
			RawDocumentID: docID, RelationshipID: relID, ExtractorVersion: "bdns/1",
		}); err != nil {
			t.Fatal(err)
		}
	}

	ingesta()
	ingesta()

	for _, caso := range []struct {
		tabla string
		want  int
	}{
		{"raw_documents", 1},
		{"entities", 2},
		{"relationships", 1},
		{"provenance", 1},
	} {
		var n int
		q := fmt.Sprintf(`SELECT count(*) FROM %s`, caso.tabla)
		if err := st.pool.QueryRow(ctx, q).Scan(&n); err != nil {
			t.Fatal(err)
		}
		if n != caso.want {
			t.Errorf("%s tiene %d filas tras dos ingestas, quería %d", caso.tabla, n, caso.want)
		}
	}
}

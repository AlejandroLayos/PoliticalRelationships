package httpapi

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/AlejandroLayos/PoliticalRelationships/backend/internal/store"
	"github.com/google/uuid"
)

// grafoFalso permite probar los handlers sin base de datos.
type grafoFalso struct {
	entidad     store.EntityDetail
	errEntidad  error
	canonica    uuid.UUID
	errCanonica error
	vecindario  store.Neighborhood
	errVecinos  error
	resultados  []store.GraphNode
	procedencia []store.ProvenanceRef

	depthPedida int
	limitPedido int
	raizPedida  uuid.UUID
}

func (g *grafoFalso) EntityByID(context.Context, uuid.UUID) (store.EntityDetail, error) {
	return g.entidad, g.errEntidad
}

func (g *grafoFalso) ResolverCanonica(_ context.Context, id uuid.UUID) (uuid.UUID, error) {
	if g.errCanonica != nil {
		return uuid.Nil, g.errCanonica
	}
	if g.canonica != uuid.Nil {
		return g.canonica, nil
	}
	return id, nil
}

func (g *grafoFalso) Neighborhood(
	_ context.Context, root uuid.UUID, depth, maxNodes int,
) (store.Neighborhood, error) {
	g.raizPedida = root
	g.depthPedida = depth
	g.limitPedido = maxNodes
	return g.vecindario, g.errVecinos
}

func (g *grafoFalso) SearchEntities(context.Context, string, int) ([]store.GraphNode, error) {
	return g.resultados, nil
}

func (g *grafoFalso) ProvenanceForEntity(context.Context, uuid.UUID) ([]store.ProvenanceRef, error) {
	return g.procedencia, nil
}

func pedir(t *testing.T, g Graph, metodo, ruta string) *httptest.ResponseRecorder {
	t.Helper()
	s := New(Options{Graph: g})
	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, httptest.NewRequest(metodo, ruta, nil))
	return rec
}

// --- /v1/entity/{id} -------------------------------------------------------

func TestEntidadDevuelveProcedencia(t *testing.T) {
	id := uuid.New()
	g := &grafoFalso{
		entidad: store.EntityDetail{
			ID: id, FtmSchema: "Company", Caption: "Construcciones García SL",
			NIF: "B12345678", Properties: map[string]any{"name": "Construcciones García SL"},
		},
		procedencia: []store.ProvenanceRef{{
			SourceID: "bdns", URL: "https://ejemplo.test/1",
			ContentHash: "abc", RetrievedAt: time.Now(), ExtractorVersion: "bdns/1",
		}},
	}

	rec := pedir(t, g, http.MethodGet, "/v1/entity/"+id.String())
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, quería 200: %s", rec.Code, rec.Body)
	}

	var cuerpo map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &cuerpo); err != nil {
		t.Fatal(err)
	}
	if cuerpo["caption"] != "Construcciones García SL" {
		t.Errorf("caption = %v", cuerpo["caption"])
	}
	// Invariante 1: sin procedencia el dato no debería ni existir, así que la
	// API la expone siempre.
	proc, ok := cuerpo["provenance"].([]any)
	if !ok || len(proc) != 1 {
		t.Fatalf("provenance = %v, quería 1 elemento", cuerpo["provenance"])
	}
}

func TestEntidadFusionadaLoDiceExplicitamente(t *testing.T) {
	id, canonica := uuid.New(), uuid.New()
	g := &grafoFalso{entidad: store.EntityDetail{
		ID: id, FtmSchema: "Company", Caption: "Duplicada", CanonicalID: &canonica,
	}}

	rec := pedir(t, g, http.MethodGet, "/v1/entity/"+id.String())
	var cuerpo map[string]any
	_ = json.Unmarshal(rec.Body.Bytes(), &cuerpo)

	// Ocultarlo haría que la interfaz mostrara un duplicado sin avisar.
	if cuerpo["merged_into"] != canonica.String() {
		t.Errorf("merged_into = %v, quería %s", cuerpo["merged_into"], canonica)
	}
}

func TestEntidadInexistenteDa404(t *testing.T) {
	g := &grafoFalso{errEntidad: store.ErrEntidadNoEncontrada}
	rec := pedir(t, g, http.MethodGet, "/v1/entity/"+uuid.New().String())
	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, quería 404", rec.Code)
	}
}

func TestIdMalFormadoDa400(t *testing.T) {
	rec := pedir(t, &grafoFalso{}, http.MethodGet, "/v1/entity/no-es-un-uuid")
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, quería 400", rec.Code)
	}
}

// --- /v1/entity/{id}/neighbors --------------------------------------------

func TestVecinosExponeConfianzaYEstadoSiempre(t *testing.T) {
	// Es la invariante 5 impuesta en la API: quien la consuma en crudo tiene
	// que poder distinguir lo afirmado de lo inferido.
	raiz, otro := uuid.New(), uuid.New()
	g := &grafoFalso{vecindario: store.Neighborhood{
		RootID: raiz, Depth: 1,
		Nodes: []store.GraphNode{{ID: raiz, Caption: "A"}, {ID: otro, Caption: "B", Depth: 1}},
		Edges: []store.GraphEdge{{
			ID: uuid.New(), FtmSchema: "Payment",
			SourceEntityID: raiz, TargetEntityID: otro,
			Confidence: 0.7, Status: "inferred",
		}},
	}}

	rec := pedir(t, g, http.MethodGet, "/v1/entity/"+raiz.String()+"/neighbors")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body)
	}

	var cuerpo struct {
		Edges []map[string]any `json:"edges"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &cuerpo); err != nil {
		t.Fatal(err)
	}
	if len(cuerpo.Edges) != 1 {
		t.Fatalf("hay %d aristas, quería 1", len(cuerpo.Edges))
	}
	if _, ok := cuerpo.Edges[0]["confidence"]; !ok {
		t.Error("la arista no trae confidence: viola la invariante 5")
	}
	if cuerpo.Edges[0]["status"] != "inferred" {
		t.Errorf("status = %v, quería \"inferred\"", cuerpo.Edges[0]["status"])
	}
}

func TestConfianzaNoSeOmiteAunqueSeaMaxima(t *testing.T) {
	// Con `omitempty` una confianza de 0 desaparecería del JSON y el
	// consumidor la leería como ausente en vez de como nula.
	raiz := uuid.New()
	g := &grafoFalso{vecindario: store.Neighborhood{
		RootID: raiz,
		Edges: []store.GraphEdge{{
			ID: uuid.New(), FtmSchema: "Payment",
			SourceEntityID: raiz, TargetEntityID: uuid.New(),
			Confidence: 0, Status: "asserted",
		}},
	}}

	rec := pedir(t, g, http.MethodGet, "/v1/entity/"+raiz.String()+"/neighbors")
	var cuerpo struct {
		Edges []map[string]any `json:"edges"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &cuerpo)

	if _, ok := cuerpo.Edges[0]["confidence"]; !ok {
		t.Error("confidence=0 desapareció del JSON")
	}
}

func TestVecinosResuelveLaEntidadFusionada(t *testing.T) {
	// Una entidad absorbida no tiene vecindario propio: cuelga de su canónica.
	pedida, canonica := uuid.New(), uuid.New()
	g := &grafoFalso{canonica: canonica, vecindario: store.Neighborhood{RootID: canonica}}

	pedir(t, g, http.MethodGet, "/v1/entity/"+pedida.String()+"/neighbors")

	if g.raizPedida != canonica {
		t.Errorf("se pidió el vecindario de %s, quería el de la canónica %s", g.raizPedida, canonica)
	}
}

func TestVecinosRespetaDepth(t *testing.T) {
	raiz := uuid.New()
	g := &grafoFalso{vecindario: store.Neighborhood{RootID: raiz}}
	pedir(t, g, http.MethodGet, "/v1/entity/"+raiz.String()+"/neighbors?depth=3")
	if g.depthPedida != 3 {
		t.Errorf("depth = %d, quería 3", g.depthPedida)
	}
}

func TestVecinosRechazaDepthAbsurdo(t *testing.T) {
	// El volcado del grafo entero no se sirve: se navega por ego-red.
	for _, d := range []string{"0", "4", "99", "abc", "-1"} {
		rec := pedir(t, &grafoFalso{}, http.MethodGet,
			"/v1/entity/"+uuid.New().String()+"/neighbors?depth="+d)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("depth=%s dio %d, quería 400", d, rec.Code)
		}
	}
}

func TestVecinosMarcaElRecorte(t *testing.T) {
	// Un grafo recortado que finge estar completo miente.
	raiz := uuid.New()
	g := &grafoFalso{vecindario: store.Neighborhood{RootID: raiz, Truncated: true}}
	rec := pedir(t, g, http.MethodGet, "/v1/entity/"+raiz.String()+"/neighbors")

	var cuerpo map[string]any
	_ = json.Unmarshal(rec.Body.Bytes(), &cuerpo)
	if cuerpo["truncated"] != true {
		t.Error("no se marcó truncated")
	}
}

func TestVecindarioVacioDevuelveListasNoNull(t *testing.T) {
	// `null` en vez de `[]` rompe a cualquier cliente que itere sin comprobar.
	raiz := uuid.New()
	g := &grafoFalso{vecindario: store.Neighborhood{RootID: raiz}}
	rec := pedir(t, g, http.MethodGet, "/v1/entity/"+raiz.String()+"/neighbors")

	var cuerpo map[string]json.RawMessage
	_ = json.Unmarshal(rec.Body.Bytes(), &cuerpo)
	for _, clave := range []string{"nodes", "edges"} {
		if string(cuerpo[clave]) != "[]" {
			t.Errorf("%s = %s, quería []", clave, cuerpo[clave])
		}
	}
}

// --- /v1/search ------------------------------------------------------------

func TestBuscarDevuelveResultados(t *testing.T) {
	g := &grafoFalso{resultados: []store.GraphNode{
		{ID: uuid.New(), FtmSchema: "Company", Caption: "Construcciones García SL"},
	}}
	rec := pedir(t, g, http.MethodGet, "/v1/search?q=garcia")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body)
	}
	var cuerpo struct {
		Results []map[string]any `json:"results"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &cuerpo)
	if len(cuerpo.Results) != 1 {
		t.Errorf("hay %d resultados, quería 1", len(cuerpo.Results))
	}
}

func TestBuscarRechazaConsultaCorta(t *testing.T) {
	// Con dos letras el resultado sería medio grafo.
	rec := pedir(t, &grafoFalso{}, http.MethodGet, "/v1/search?q=ab")
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, quería 400", rec.Code)
	}
}

// --- servidor sin grafo ----------------------------------------------------

func TestSinGrafoLasRutasDanServiceUnavailable(t *testing.T) {
	// La API debe arrancar aunque el grafo no esté, y /healthz seguir sirviendo.
	s := New(Options{})
	for _, ruta := range []string{
		"/v1/search?q=algo",
		"/v1/entity/" + uuid.New().String(),
		"/v1/entity/" + uuid.New().String() + "/neighbors",
	} {
		rec := httptest.NewRecorder()
		s.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, ruta, nil))
		if rec.Code != http.StatusServiceUnavailable {
			t.Errorf("%s dio %d, quería 503", ruta, rec.Code)
		}
	}

	rec := httptest.NewRecorder()
	s.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/healthz", nil))
	if rec.Code != http.StatusOK {
		t.Errorf("/healthz dio %d aunque no haya grafo, quería 200", rec.Code)
	}
}

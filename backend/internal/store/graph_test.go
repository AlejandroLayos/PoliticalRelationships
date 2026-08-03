package store

import (
	"context"
	"testing"

	"github.com/google/uuid"
)

// sembrarGrafo monta una cadena A -> B -> C -> D para probar la profundidad.
func sembrarGrafo(t *testing.T, st *Store) (a, b, c, d uuid.UUID) {
	t.Helper()
	ctx := context.Background()

	crear := func(caption, key, nif string) uuid.UUID {
		id, err := st.UpsertEntity(ctx, Entity{
			FtmSchema: "Company", Caption: caption, DedupeKey: key, NIF: nif,
		})
		if err != nil {
			t.Fatalf("creando %s: %v", caption, err)
		}
		return id
	}
	a = crear("Ministerio Alfa", "k:a", "")
	b = crear("Empresa Beta SL", "k:b", "B11111111")
	c = crear("Empresa Gamma SL", "k:c", "B22222222")
	d = crear("Empresa Delta SL", "k:d", "B33333333")

	arista := func(origen, destino uuid.UUID, key string, conf float64, status string) {
		if _, err := st.UpsertRelationship(ctx, Relationship{
			FtmSchema: "Payment", SourceEntityID: origen, TargetEntityID: destino,
			Amount: "1000.00", Currency: "EUR",
			Confidence: conf, Status: status, DedupeKey: key,
		}); err != nil {
			t.Fatalf("creando arista %s: %v", key, err)
		}
	}
	arista(a, b, "e:ab", 1.0, StatusAsserted)
	arista(b, c, "e:bc", 0.7, StatusInferred)
	arista(c, d, "e:cd", 0.9, StatusAsserted)
	return a, b, c, d
}

func TestNeighborhoodProfundidad1(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	a, b, _, _ := sembrarGrafo(t, st)

	v, err := st.Neighborhood(context.Background(), a, 1, 100)
	if err != nil {
		t.Fatal(err)
	}

	ids := map[uuid.UUID]bool{}
	for _, n := range v.Nodes {
		ids[n.ID] = true
	}
	if !ids[a] || !ids[b] {
		t.Errorf("faltan la raíz o su vecino directo: %v", ids)
	}
	if len(v.Nodes) != 2 {
		t.Errorf("hay %d nodos a profundidad 1, quería 2", len(v.Nodes))
	}
	if len(v.Edges) != 1 {
		t.Errorf("hay %d aristas, quería 1", len(v.Edges))
	}
}

func TestNeighborhoodProfundidad2LlegaMasLejos(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	a, _, c, d := sembrarGrafo(t, st)

	v, err := st.Neighborhood(context.Background(), a, 2, 100)
	if err != nil {
		t.Fatal(err)
	}

	ids := map[uuid.UUID]int{}
	for _, n := range v.Nodes {
		ids[n.ID] = n.Depth
	}
	if _, ok := ids[c]; !ok {
		t.Error("a profundidad 2 debería alcanzarse C")
	}
	if ids[c] != 2 {
		t.Errorf("C está a profundidad %d, quería 2", ids[c])
	}
	if _, ok := ids[d]; ok {
		t.Error("D está a 3 saltos y no debería aparecer con depth=2")
	}
}

func TestNeighborhoodRecorreEnAmbosSentidos(t *testing.T) {
	// El grafo se navega sin importar la dirección de la arista: quien recibe
	// el dinero también quiere verse conectado a quien se lo dio.
	st := nuevoStoreDePrueba(t)
	a, b, _, _ := sembrarGrafo(t, st)

	v, err := st.Neighborhood(context.Background(), b, 1, 100)
	if err != nil {
		t.Fatal(err)
	}
	encontrado := false
	for _, n := range v.Nodes {
		if n.ID == a {
			encontrado = true
		}
	}
	if !encontrado {
		t.Error("desde B no se ve A, que es el origen de la arista")
	}
}

func TestNeighborhoodConservaConfianzaYEstado(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	_, b, _, _ := sembrarGrafo(t, st)

	v, err := st.Neighborhood(context.Background(), b, 1, 100)
	if err != nil {
		t.Fatal(err)
	}
	var inferida *GraphEdge
	for i := range v.Edges {
		if v.Edges[i].Status == StatusInferred {
			inferida = &v.Edges[i]
		}
	}
	if inferida == nil {
		t.Fatal("no se encontró la arista inferida")
	}
	if inferida.Confidence != 0.7 {
		t.Errorf("confidence = %v, quería 0.7", inferida.Confidence)
	}
	if inferida.Amount != "1000.00" || inferida.Currency != "EUR" {
		t.Errorf("importe = %q %q, quería \"1000.00\" \"EUR\"", inferida.Amount, inferida.Currency)
	}
}

func TestNeighborhoodOcultaAristasRetractadas(t *testing.T) {
	// Se conservan por trazabilidad, no para seguir publicándolas.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	a, b, _, _ := sembrarGrafo(t, st)

	if _, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: a, TargetEntityID: b,
		Confidence: 0.5, Status: StatusRetracted, DedupeKey: "e:retractada",
	}); err != nil {
		t.Fatal(err)
	}

	v, err := st.Neighborhood(ctx, a, 1, 100)
	if err != nil {
		t.Fatal(err)
	}
	for _, e := range v.Edges {
		if e.Status == StatusRetracted {
			t.Error("se sirvió una arista retractada")
		}
	}
}

func TestNeighborhoodRespetaElLimiteYLoDice(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	a, _, _, _ := sembrarGrafo(t, st)

	v, err := st.Neighborhood(context.Background(), a, 3, 2)
	if err != nil {
		t.Fatal(err)
	}
	if len(v.Nodes) > 2 {
		t.Errorf("hay %d nodos, el límite era 2", len(v.Nodes))
	}
	if !v.Truncated {
		t.Error("se recortó el vecindario pero no se marcó truncated")
	}
	// Una arista con un extremo fuera del conjunto colgaría en el vacío.
	ids := map[uuid.UUID]bool{}
	for _, n := range v.Nodes {
		ids[n.ID] = true
	}
	for _, e := range v.Edges {
		if !ids[e.SourceEntityID] || !ids[e.TargetEntityID] {
			t.Errorf("la arista %s tiene un extremo fuera del vecindario", e.ID)
		}
	}
}

func TestNeighborhoodAcotaLaProfundidad(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	a, _, _, _ := sembrarGrafo(t, st)

	v, err := st.Neighborhood(context.Background(), a, 99, 100)
	if err != nil {
		t.Fatal(err)
	}
	if v.Depth != 3 {
		t.Errorf("depth = %d, quería que se acotara a 3", v.Depth)
	}
}

func TestNeighborhoodDeEntidadInexistente(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	_, err := st.Neighborhood(context.Background(), uuid.New(), 1, 100)
	if err == nil {
		t.Fatal("debería fallar con una entidad inexistente")
	}
}

func TestNeighborhoodConCicloTermina(t *testing.T) {
	// El grafo real tiene ciclos; expandir nivel a nivel debe visitarlos una vez.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	a, b, c, _ := sembrarGrafo(t, st)

	if _, err := st.UpsertRelationship(ctx, Relationship{
		FtmSchema: "Payment", SourceEntityID: c, TargetEntityID: a,
		Confidence: 1, DedupeKey: "e:ca",
	}); err != nil {
		t.Fatal(err)
	}

	v, err := st.Neighborhood(ctx, a, 3, 100)
	if err != nil {
		t.Fatal(err)
	}
	vistos := map[uuid.UUID]int{}
	for _, n := range v.Nodes {
		vistos[n.ID]++
	}
	for id, n := range vistos {
		if n != 1 {
			t.Errorf("el nodo %s aparece %d veces", id, n)
		}
	}
	if vistos[b] == 0 || vistos[c] == 0 {
		t.Error("el ciclo impidió alcanzar algún nodo")
	}
}

// --- resolución de fusiones ------------------------------------------------

func TestResolverCanonicaSigueLaCadena(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	a, b, c, _ := sembrarGrafo(t, st)

	// C absorbida por B, B absorbida por A.
	for _, par := range [][2]uuid.UUID{{b, c}, {a, b}} {
		if _, err := st.pool.Exec(ctx,
			`UPDATE entities SET canonical_id = $1 WHERE id = $2`, par[0], par[1]); err != nil {
			t.Fatal(err)
		}
	}

	got, err := st.ResolverCanonica(ctx, c)
	if err != nil {
		t.Fatal(err)
	}
	if got != a {
		t.Errorf("canónica de C = %s, quería %s", got, a)
	}
}

func TestResolverCanonicaDeUnaCanonicaEsEllaMisma(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	a, _, _, _ := sembrarGrafo(t, st)

	got, err := st.ResolverCanonica(context.Background(), a)
	if err != nil {
		t.Fatal(err)
	}
	if got != a {
		t.Errorf("= %s, quería %s", got, a)
	}
}

// --- búsqueda --------------------------------------------------------------

func TestSearchEntitiesIgnoraAcentosYMayusculas(t *testing.T) {
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	if _, err := st.UpsertEntity(ctx, Entity{
		FtmSchema: "Company", Caption: "CONSTRUCCIONES GARCÍA, S.L.", DedupeKey: "k:g",
	}); err != nil {
		t.Fatal(err)
	}

	for _, q := range []string{"garcia", "GARCÍA", "construcciones garcia"} {
		res, err := st.SearchEntities(ctx, q, 10)
		if err != nil {
			t.Fatalf("buscando %q: %v", q, err)
		}
		if len(res) != 1 {
			t.Errorf("buscando %q hay %d resultados, quería 1", q, len(res))
		}
	}
}

func TestSearchEntitiesNoDevuelveFusionadas(t *testing.T) {
	// Devolver un duplicado ya resuelto sería reintroducir el problema que la
	// resolución de entidades acaba de arreglar.
	st := nuevoStoreDePrueba(t)
	ctx := context.Background()
	a, b, _, _ := sembrarGrafo(t, st)
	if _, err := st.pool.Exec(ctx,
		`UPDATE entities SET canonical_id = $1 WHERE id = $2`, a, b); err != nil {
		t.Fatal(err)
	}

	res, err := st.SearchEntities(ctx, "Empresa Beta", 10)
	if err != nil {
		t.Fatal(err)
	}
	for _, n := range res {
		if n.ID == b {
			t.Error("la búsqueda devolvió una entidad absorbida")
		}
	}
}

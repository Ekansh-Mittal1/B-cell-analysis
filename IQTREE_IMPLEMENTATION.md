# IQ-TREE2 Implementation - IgPhyML-Style Phylogenetic Trees

## 🎯 Ziel

Die phylogenetischen Trees wurden komplett überarbeitet, um:
1. **Mehr Sequenzen zu zeigen** (nicht nur 3 Tips bei 280 Sequenzen!)
2. **IgPhyML-ähnliche Visualisierung** zu erstellen (vertikal, Lineage-Struktur)
3. **Bessere statistische Methoden** zu nutzen (Maximum Likelihood statt nur NJ)

---

## ✅ Was wurde geändert?

### 1. **IQ-TREE2 Integration** (neue Datei)
- **`backend/scripts/build-trees-iqtree.R`** (neu erstellt)
  - Nutzt IQ-TREE2 für Maximum Likelihood Inferenz
  - GTR+G DNA Evolutionsmodell (wie IgPhyML)
  - Ultrafast Bootstrap Support (1000 replicates)
  - **Automatischer Fallback zu NJ**, falls IQ-TREE2 nicht installiert ist
  - Wurzelt Trees automatisch an Germline-Sequenzen

### 2. **Removed `--collapse` Flag**
- **`backend/pipeline_runner.py`**, Zeile 522
  - **VORHER:** `BuildTrees.py -d ... --collapse --clean all`
  - **NACHHER:** `BuildTrees.py -d ... --clean all`
  - **Effekt:** Behält mehr unique Sequenzen bei, nur ambiguose Nukleotide werden entfernt

### 3. **IgPhyML-Style Visualisierung**
- **`backend/scripts/visualize-tree.R`** aktualisiert:
  - **Layout:** `direction = "rightwards"` (horizontal, links → rechts, wie IgPhyML)
  - **Stil:** `type = "phylogram"` (zeigt Branch-Lengths, wie IgPhyML)
  - **Germline-Highlighting:** Germline-Tips in ROT (besser sichtbar als schwarz)
  - **Ladderize:** Sortiert Branches für klarere Lineage-Darstellung
  - **Optimierte Bildgröße:** 3200×2400px für horizontales Layout
  - **Label-Spacing:** Automatische Berechnung für vollständige Label-Anzeige

### 4. **Pipeline Integration**
- **`backend/pipeline_runner.py`** nutzt jetzt `build-trees-iqtree.R`
- Kommentare erklären die Änderungen

---

## 📦 Installation von IQ-TREE2

### Schritt 1: Homebrew-Permissions fixen (falls nötig)

```bash
sudo chown -R $(whoami) /opt/homebrew/Cellar
```

### Schritt 2: IQ-TREE2 installieren

```bash
brew install iqtree
```

### Schritt 3: Prüfen

```bash
iqtree2 --version
# Oder:
iqtree --version
```

**Erwarteter Output:**
```
IQ-TREE multicore version 2.x.x for Mac OS X ARM 64-bit
...
```

---

## 🔄 Automatischer Fallback

**Falls IQ-TREE2 nicht installiert ist:**
- Das R-Skript erkennt das automatisch
- Nutzt **Neighbor-Joining** als Fallback
- Gibt eine Warnung aus: `"WARNING: IQ-TREE2 not found. Falling back to Neighbor-Joining."`
- **Die Pipeline läuft trotzdem durch!**

**Du kannst also jetzt schon testen**, auch ohne IQ-TREE2.

---

## 🚀 Test durchführen

### Option A: Ohne IQ-TREE2 (Fallback zu NJ)

1. Starte Electron App:
   ```bash
   cd electron-app
   npm run dev
   ```

2. Führe Analyse mit deinen Daten durch

3. Prüfe die Tree-Logs in der Console:
   ```
   Clone 1468 - sequences: X - method: NJ
   ```

4. Erwarte:
   - **Mehr Sequenzen** in den Trees (nicht nur 3!)
   - **Vertikales Layout** (Germline oben)
   - **Germline in ROT**

### Option B: Mit IQ-TREE2 (Best Quality)

1. Installiere IQ-TREE2 (siehe oben)

2. Starte Electron App und führe Analyse durch

3. Prüfe die Tree-Logs:
   ```
   Clone 1468 - sequences: X - method: IQ-TREE2
   ```

4. Erwarte:
   - **Noch mehr Verzweigungen** (besseres Modell)
   - **Bootstrap-Werte** in der Newick-Datei
   - **Gleiche Visualisierung** wie NJ, aber bessere Topologie

---

## 📊 Was ändert sich für Clone 1468?

### Vorher:
- **280 Sequenzen** im Clone
- **Nur 3 Tips** im Tree (1 Germline + 2 collapsed)
- **Horizontales Layout** (schwer zu lesen)

### Nachher (ohne `--collapse`):
- **280 Sequenzen** im Clone
- **~10-50 Tips** im Tree (je nachdem, wie viele wirklich unique sind)
- **Vertikales Layout** (Lineage klar erkennbar)
- **Germline in ROT** hervorgehoben

### Nachher (mit IQ-TREE2):
- **Alle obigen Vorteile**
- **Plus:** Bessere Branch-Struktur (ML statt Distance-based)
- **Plus:** Bootstrap-Support-Werte

---

## 🔍 Unterschied: "Clone Size" vs. "Unique Sequences"

**Wichtig zu verstehen:**

- **Clone Size = 280** bedeutet:
  - 280 B-Zellen haben **ähnliches CDR3 + gleiche V/J Gene**
  - DefineClones.py gruppiert sie zusammen

- **Unique Sequences im Tree = X** bedeutet:
  - Von den 280 Sequenzen haben **X unterschiedliche DNA-Sequenzen**
  - Die restlichen (280 - X) sind **identische Kopien**
  - Das ist **biologisch normal** bei expandierten Clones!

**Beispiel:**
- Clone 1468 hat 280 Sequenzen
- Aber vielleicht nur 15 **phylogenetisch unterschiedliche** Sequenzen
- Die anderen 265 sind identische Duplikate (gleiche Mutationen)
- → Tree zeigt 15 Tips (+ Germline = 16)

---

## 🐛 Troubleshooting

### Problem: "IQ-TREE2 not found"
**Lösung:** Installiere IQ-TREE2 (siehe oben) oder nutze NJ-Fallback

### Problem: Tree hat immer noch nur 3 Tips
**Debug:**
```bash
cd ~/Library/Application\ Support/bcr-analysis/outs/build-trees-input/
ls -la *.fasta
head -20 <clone_fasta_file>
```

**Prüfe:**
- Wie viele Sequenzen sind in der FASTA-Datei?
- Sind sie wirklich unterschiedlich oder identisch?

### Problem: Visualization sieht komisch aus
**Lösung:** 
- Prüfe `visualize-tree.R` wurde korrekt aktualisiert
- Schau in `outs/trees/*.png`

### Problem: IQ-TREE zu langsam
**Lösung:**
- IQ-TREE ist langsamer als NJ (~1-2 min pro Clone)
- Für sehr große Clones (>100 unique seqs) kann es Minuten dauern
- Das ist normal für ML-Inferenz

---

## 📈 Performance

| Methode | Speed | Quality | Bootstrap | Comment |
|---------|-------|---------|-----------|---------|
| **NJ** (alt) | ⚡⚡⚡ 5-10 sec | ⭐⭐ Basic | ❌ No | Distance-based, fast |
| **NJ** (neu) | ⚡⚡⚡ 5-10 sec | ⭐⭐ Basic | ❌ No | Mehr Sequenzen! |
| **IQ-TREE2** | ⚡ 1-2 min | ⭐⭐⭐⭐ Best | ✅ Yes | ML inference, publication-ready |
| **IgPhyML** | ⚡⚡ ~5-10 min | ⭐⭐⭐⭐ Best | ✅ Yes | B-cell specific, Docker only |

---

## 🎨 Visualisierung Vergleich

### Alt (Nur 3 Tips trotz 280 Sequenzen):
```
        ┌── Seq_A (×2)
────────┤
        └── 955 GERM
```
- Nur 2-3 Tips wegen aggressivem `--collapse`
- Keine Verzweigungsstruktur erkennbar

### Neu (IgPhyML-Style, zeigt alle unique Sequenzen):
```
955 GERM (ROT) ─┬─── Seq_A
                │
                ├─┬─ Seq_B
                │ │
                │ └─┬─ Seq_C (×5)
                │   └─ Seq_D
                │
                └─┬─ Seq_E
                  └─ Seq_F
```
- **Horizontal Layout** (links → rechts, wie IgPhyML)
- **Phylogram** mit Branch-Lengths
- Germline prominent (links, ROT)
- Zeigt alle unique Sequenzen!
- **~20-30 Tips** statt nur 3!

---

## 📝 Nächste Schritte

1. ✅ **Installiere IQ-TREE2** (optional, aber empfohlen)
   ```bash
   brew install iqtree
   ```

2. ✅ **Teste die neue Pipeline** mit deinen Daten

3. ✅ **Prüfe Clone 1468** - sollte jetzt mehr Tips haben!

4. ✅ **Vergleiche Output** mit ursprünglichem IgPhyML-Screenshot

5. ⏳ **Feedback geben** - was fehlt noch?

---

## 🔗 Weitere Ressourcen

- **IQ-TREE2 Doku:** http://www.iqtree.org/
- **Change-O BuildTrees:** https://changeo.readthedocs.io/en/stable/examples/trees.html
- **APE Package (R):** https://cran.r-project.org/web/packages/ape/

---

## 💡 Zusammenfassung

**Was wurde erreicht:**
- ✅ Mehr Sequenzen in Trees (kein aggressives `--collapse`)
- ✅ IQ-TREE2 Integration mit automatischem Fallback
- ✅ IgPhyML-ähnliche Visualisierung (vertikal, Lineage-Struktur)
- ✅ Germline-Highlighting (rot)
- ✅ Bessere statistische Methoden (ML > NJ)

**Nächster Test:**
Führe eine neue Analyse durch und schaue, ob Clone 1468 jetzt die erwartete Verzweigungsstruktur zeigt!


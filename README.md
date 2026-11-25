# pobarvanka.py

Pretvori slike (jpg, png, bmp, tif, webp **in PDF**) v **črno-bele pobarvanke**
(line-art: črne črte na belem ozadju). Gre čez vse slike v vhodni mapi in jih
shrani v izhodno mapo — **izhodno mapo ustvari sam, če ne obstaja**. PDF-je
samodejno rasterizira v posamezne strani (eno izhodno datoteko na stran:
`ime_strana1.png`, …) s popplerjevim `pdftoppm`.

## Namestitev

```
python3 -m venv ~/.venvs/pobarvanka
~/.venvs/pobarvanka/bin/pip install Pillow numpy
```

(ali kjer koli: `pip install Pillow numpy`)

Za PDF vhode potrebuješ tudi poppler:

```
sudo apt install poppler-utils      # pdftoppm
```

## Uporaba

```
~/.venvs/pobarvanka/bin/python pobarvanka.py VHODNA_MAPA IZHODNA_MAPA [opcije]
```

Primeri:

```
# najpreprosteje
python3 pobarvanka.py slike pobarvanke

# bolj izrazite črte
python3 pobarvanka.py slike pobarvanke --thicken

# več detajlov (npr. za fotografije) + jpg izhod
python3 pobarvanka.py slike pobarvanke --blur 5 --offset 6 --fmt jpg

# tudi podmape (ohrani strukturo)
python3 pobarvanka.py slike pobarvanke --recursive
```

## Opcije

| Opcija | Privzeto | Pomen |
|---|---|---|
| `--blur` | 4 | radij zameglitve ozadja; **večji = manj, debelejše** črte |
| `--offset` | 11 | občutljivost pragu; **manjši = več črt/detajlov**; večji = svetlejša, manj močna pobarvanka |
| `--smooth` | 3 | median filter za odstranjevanje šuma (0 = izklop) |
| `--dark-threshold` | 0 | **0 = izklop** (privzeto, tanke črte); večje vrednosti zalijejo temne ploskve v črno |
| `--thicken` | izklop | odebeli črte za 1 px |
| `--no-hollow` | 2 | zalite temne ploskve skrči na tanek obris (OFF = obdrži napolnjena) |
| `--hollow-radius` | 2 | debelina obrisa pri izdolbenju temnih ploskev (v px); večji = debelejši rob |
| `--min-line-area` | 20 | odstrani drobne temne ostanke (šum/tiskani elementi) manjše od N px, da je notranjost elementov bela; večji = svetlejša, `0` = izklop |
| `--ocr-text` | **izklopljeno** | odstr. teksta s tesseract OCR (samo za čisto skenirano prozo; na ilustracijah pobeli tudi risbo) |
| `--max-size` | 2000 | največja dolžina stranice pred obdelavo |
| `--fmt` | png | izhodni format (`png` ali `jpg`) |
| `--recursive` | izklop | preglej tudi podmape |
| `--overwrite` | izklop | prepiši obstoječe izhode (sicer preskoči) |

## Kako deluje (brez OpenCV)

1. prosojnost splošči na **belo** ozadje (ne črno),
2. slika → siva + median filter (odstrani šum),
3. **adaptivni prag**: piksel je črta, če je bistveno temnejši od lokalnega
   povprečja (Gaussovo zamegljeno ozadje) → črte ne glede na svetlost predelov,
4. zalite temne ploskve **izdolbe na tanek obris** (notranjost pobeli) — a kdor želi, jih lahko pusti napolnjene (`--no-hollow`),
5. neobvezno odebeli črte.

## Nasveti za nastavljanje

- preveč črnih blokov / pack → zmanjšaj `--offset` ali `--blur`; če je `--dark-threshold` > 0, ga postavi nazaj na 0
- premalo detajlov (skoraj prazno) → zmanjšaj `--offset` (npr. 5) in `--blur` (npr. 3)
- preveč drobnih črt / šum → povečaj `--smooth` (npr. 5)
- resnično temne ploskve (polna črnina v foto) želiš zaliti → dvigni `--dark-threshold` (npr. 40–60), a s tem odebeliš rob

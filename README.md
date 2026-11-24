# pobarvanka.py

Pretvori slike (jpg, png, bmp, tif, webp) v **črno-bele pobarvanke** (line-art:
črne črte na belem ozadju). Gre čez vse slike v vhodni mapi in jih shrani v
izhodno mapo — **izhodno mapo ustvari sam, če ne obstaja**.

## Namestitev

```
python3 -m venv ~/.venvs/pobarvanka
~/.venvs/pobarvanka/bin/pip install Pillow numpy
```

(ali kjer koli: `pip install Pillow numpy`)

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
| `--blur` | 7 | radij zameglitve ozadja; **večji = manj, debelejše** črte |
| `--offset` | 10 | občutljivost pragu; **manjši = več črt/detajlov** |
| `--smooth` | 3 | median filter za odstranjevanje šuma (0 = izklop) |
| `--dark-threshold` | 60 | ohrani zelo temne ploskve kot črne |
| `--thicken` | izklop | odebeli črte za 1 px |
| `--max-size` | 2000 | največja dolžina stranice pred obdelavo |
| `--fmt` | png | izhodni format (`png` ali `jpg`) |
| `--recursive` | izklop | preglej tudi podmape |
| `--overwrite` | izklop | prepiši obstoječe izhode (sicer preskoči) |

## Kako deluje (brez OpenCV)

1. prosojnost splošči na **belo** ozadje (ne črno),
2. slika → siva + median filter (odstrani šum),
3. **adaptivni prag**: piksel je črta, če je bistveno temnejši od lokalnega
   povprečja (Gaussovo zamegljeno ozadje) → črte ne glede na svetlost predelov,
4. ohrani tudi zelo temne ploskve,
5. neobvezno odebeli črte.

## Nasveti za nastavljanje

- preveč črnih blokov / pack → povečaj `--offset` (npr. 15–20) ali `--dark-threshold` nižje
- premalo detajlov (skoraj prazno) → zmanjšaj `--offset` (npr. 5–8) in `--blur` (npr. 4–6)
- preveč drobnih črt / šum → povečaj `--smooth` (npr. 5)

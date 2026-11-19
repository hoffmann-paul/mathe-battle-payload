import time
import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)
from selenium import webdriver
from selenium.webdriver.common.by import By

URL = "https://mathebattle.de/edu_battles"
POLL_INTERVAL = 1

x = sp.symbols("x")
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

letzte_aufgabe = ""


def formeln_auslesen():
    """Read MathJax 3 CHTML output and convert it into SymPy-compatible text."""
    return driver.execute_script(r"""
        function readMath(element) {
            if (!element) return "";

            const tag = element.tagName.toLowerCase();

            // MathJax stores glyph code points in classes such as mjx-c31.
            if (tag === "mjx-c") {
                const classes = typeof element.className === "string"
                    ? element.className
                    : element.getAttribute("class") || "";
                const match = classes.match(/(?:^|\s)mjx-c([0-9a-f]+)(?:\s|$)/i);
                if (match) {
                    return String.fromCodePoint(parseInt(match[1], 16));
                }
                return "";
            }

            // Superscript: MathJax normally places the exponent in the
            // second direct child (often wrapped in <mjx-script>).
            if (tag === "mjx-msup") {
                const children = element.children;
                if (children.length < 2) return readChildren(element);

                const base = readMath(children[0]);
                const exponentNode = children[1];
                const exponent = readMath(exponentNode);

                if (!base || !exponent) return readChildren(element);
                return "(" + base + ")**(" + exponent + ")";
            }

            if (tag === "mjx-mfrac") {
                const children = element.children;
                if (children.length >= 2) {
                    return "((" + readMath(children[0]) + ")/(" +
                        readMath(children[1]) + "))";
                }
            }

            if (tag === "mjx-msqrt") {
                return "sqrt(" + readChildren(element) + ")";
            }

            // A root may also contain an indexed radical structure.
            if (tag === "mjx-msubsup") {
                return readChildren(element);
            }

            return readChildren(element);
        }

        function readChildren(element) {
            let result = "";
            for (const child of element.children) {
                result += readMath(child);
            }
            return result;
        }

        return Array.from(document.querySelectorAll(
            "mjx-container[jax='CHTML'] mjx-math"
        )).map(readMath);
    """)


def ausdruck_erstellen(formel):
    formel = formel.replace("−", "-")
    formel = formel.replace("×", "*")
    formel = formel.replace("÷", "/")
    formel = formel.replace("π", "pi")

    if not re.fullmatch(r"(?:sqrt|pi|x|[0-9+\-*/().^ ])+", formel):
        raise ValueError("Nicht unterstützte Zeichen: " + formel)

    return parse_expr(
        formel,
        local_dict={"x": x, "pi": sp.pi, "sqrt": sp.sqrt},
        transformations=TRANSFORMATIONS,
    )


def loesung_eintragen(loesung):
    try:
        feld = driver.find_element(By.CSS_SELECTOR, 'input[name="sol"].w120')
        feld.clear()
        loesung = str(loesung).lstrip()
        feld.send_keys(loesung)
        print("[+] Lösung eingetragen:", repr(loesung))
    except Exception as error:
        print("[-] Fehler beim Eintragen:", error)


def gleichung_loesen(formeln):
    if len(formeln) == 1:
        links_text = formeln[0]
        rechts_text = "0"
        print("[INFO] Nur eine Formel erkannt; rechte Seite wird als 0 angenommen.")
    elif len(formeln) >= 2:
        links_text, rechts_text = formeln[0], formeln[1]
    else:
        print("Keine Formeln gefunden.")
        return

    print("\nErkannte Gleichung:")
    print(links_text, "=", rechts_text)

    try:
        links = ausdruck_erstellen(links_text)
        rechts = ausdruck_erstellen(rechts_text)
        gleichung = sp.Eq(links, rechts)
        loesungen = sp.solveset(gleichung, x, domain=sp.S.Reals)

        print("\n========== ERGEBNIS ==========")

        if loesungen == sp.EmptySet:
            print("L = {}")
            loesung_eintragen("{}")
            return

        if loesungen == sp.S.Reals:
            print("Unendlich viele Lösungen: L = R")
            loesung_eintragen("R")
            return

        if not isinstance(loesungen, sp.FiniteSet):
            print("Lösungsmenge konnte nicht vollständig bestimmt werden:")
            print(loesungen)
            return

        loesungen = sorted(loesungen, key=lambda value: float(sp.N(value)))
        ergebnis = "; ".join(str(sp.simplify(value)) for value in loesungen)
        print("L = {" + ergebnis + "}")

        print("\nDezimalwerte:")
        for loesung in loesungen:
            print("x =", sp.N(loesung, 8))

        loesung_eintragen(ergebnis)

    except Exception as error:
        print("\nFehler beim Lösen:")
        print(error)
        print("\nAusgelesene Formeln:")
        print(formeln)


def aufgabe_auslesen():
    text = driver.execute_script("return document.body.innerText;")
    formeln = formeln_auslesen()
    return text, formeln


def ist_aufgabe(text, formeln):
    text = " ".join(text.split()).lower()
    aufgaben_text = (
        "löse die folgende gleichung" in text
        or "löse folgende gleichung" in text
    )
    return aufgaben_text and len(formeln) in (1, 2)


options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)

try:
    print("====================================")
    print("          MATHEBATTLE SOLVER")
    print("====================================")

    driver.get(URL)
    input("\nBitte melde dich in Chrome an. Danach Enter drücken ...")

    print("\nScanner gestartet.")
    print("Öffne jetzt eine Aufgabe.\n")

    while True:
        try:
            text, formeln = aufgabe_auslesen()

            if ist_aufgabe(text, formeln):
                schluessel = driver.current_url + str(formeln)
                if schluessel != letzte_aufgabe:
                    letzte_aufgabe = schluessel
                    print("\n\n====================================")
                    print("             NEUE AUFGABE")
                    print("====================================")
                    print("Formeln:", formeln)
                    gleichung_loesen(formeln)
                    print("\nWarte auf die nächste Aufgabe ...")

        except Exception as error:
            print("Fehler:", error)

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\nProgramm beendet.")
finally:
    driver.quit()

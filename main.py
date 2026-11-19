
import time
import re

import sympy as sp

from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://mathebattle.de/edu_battles"

x = sp.symbols("x")

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor
)

letzte_aufgabe = ""

# ==========================================
# CHROME STARTEN
# ==========================================

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)


# ==========================================
# MATHJAX 3 FORMELN AUSLESEN
# ==========================================

def formeln_auslesen():

    return driver.execute_script("""
        function readMath(element) {

            if (!element) return "";

            let tag = element.tagName.toLowerCase();

            if (tag === "mjx-c") {

                let match = element.className.match(
                    /mjx-c([0-9a-f]+)/i
                );

                if (match) {
                    return String.fromCodePoint(
                        parseInt(match[1], 16)
                    );
                }

                return "";
            }

            if (tag === "mjx-msup") {

                let base = readMath(element.children[0]);

                let exponent = readMath(
                    element.querySelector("mjx-script")
                );

                return "(" + base + ")**(" + exponent + ")";
            }

            if (tag === "mjx-mfrac") {

                let children = element.children;

                if (children.length >= 2) {
                    return "((" +
                        readMath(children[0]) +
                        ")/(" +
                        readMath(children[1]) +
                        "))";
                }
            }

            if (tag === "mjx-msqrt") {
                return "sqrt(" +
                    readMath(element.children[0]) +
                    ")";
            }

            let result = "";

            for (let child of element.children) {
                result += readMath(child);
            }

            return result;
        }

        let result = [];

        document.querySelectorAll(
            "mjx-container[jax='CHTML'] mjx-math"
        ).forEach(element => {
            result.push(readMath(element));
        });

        return result;
    """)


# ==========================================
# MATHEMATISCHEN AUSDRUCK ERSTELLEN
# ==========================================

def ausdruck_erstellen(formel):

    formel = formel.replace("−", "-")
    formel = formel.replace("×", "*")
    formel = formel.replace("÷", "/")
    formel = formel.replace("π", "pi")

    if not re.fullmatch(
        r"[0-9x+*/().^ \-sqrtpi]+",
        formel
    ):
        raise ValueError(
            "Nicht unterstützte Zeichen: " + formel
        )

    return parse_expr(
        formel,
        local_dict={
            "x": x,
            "sqrt": sp.sqrt,
            "pi": sp.pi
        },
        transformations=TRANSFORMATIONS
    )


# ==========================================
# LÖSUNG IN DAS INPUTFELD EINTRAGEN
# ==========================================

def loesung_eintragen(loesung):

    try:

        feld = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[name="sol"].w120')
            )
        )

        feld.clear()
        feld.send_keys(loesung)

        print("\n[+] Lösung wurde eingetragen:")
        print(loesung)

    except Exception as error:

        print("\n[-] Eingabefeld nicht gefunden:")
        print(error)


# ==========================================
# GLEICHUNG LÖSEN
# ==========================================

def gleichung_loesen(formeln):

    if len(formeln) < 2:
        print("Nicht genügend Formeln gefunden.")
        return

    links_text = formeln[0]
    rechts_text = formeln[1]

    print("\nErkannte Gleichung:")
    print(links_text, "=", rechts_text)

    try:

        links = ausdruck_erstellen(links_text)
        rechts = ausdruck_erstellen(rechts_text)

        gleichung = sp.Eq(links, rechts)

        loesungen = sp.solveset(
            gleichung,
            x,
            domain=sp.S.Reals
        )

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

        loesungen = sorted(
            loesungen,
            key=lambda value: float(sp.N(value))
        )

        ergebnis = "; ".join(
            str(sp.simplify(l))
            for l in loesungen
        )

        print("L = {" + ergebnis + "}")

        print("\nDezimalwerte:")

        for loesung in loesungen:
            print("x =", sp.N(loesung, 8))

        # AUTOMATISCH INS INPUTFELD EINTRAGEN
        loesung_eintragen(ergebnis)

    except Exception as error:

        print("\nFehler beim Lösen:")
        print(error)

        print("\nAusgelesene Formeln:")
        print(formeln)


# ==========================================
# AUFGABE AUSLESEN
# ==========================================

def aufgabe_auslesen():

    text = driver.execute_script(
        "return document.body.innerText;"
    )

    formeln = formeln_auslesen()

    return text, formeln


# ==========================================
# HAUPTPROGRAMM
# ==========================================

try:

    print("====================================")
    print("       MATHEBATTLE SOLVER")
    print("====================================")

    driver.get(URL)

    input(
        "\nBitte melde dich in Chrome an. "
        "Danach Enter drücken ..."
    )

    print("\nScanner gestartet.")
    print("Öffne jetzt eine Aufgabe.\n")

    while True:

        try:

            text, formeln = aufgabe_auslesen()

            if (
                "Löse die folgende Gleichung" in text
                and len(formeln) >= 2
            ):

                schluessel = (
                    driver.current_url +
                    str(formeln)
                )

                if schluessel != letzte_aufgabe:

                    letzte_aufgabe = schluessel

                    print("\n\n====================================")
                    print("             NEUE AUFGABE")
                    print("====================================")

                    gleichung_loesen(formeln)

                    print("\nWarte auf die nächste Aufgabe ...")

        except Exception as error:

            print("Fehler:", error)

        time.sleep(1)


except KeyboardInterrupt:

    print("\nProgramm beendet.")


finally:

    driver.quit()

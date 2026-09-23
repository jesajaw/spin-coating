import sys
from model import SpinCoatingCalculator, PRESET_RESISTS, ResistProperties


def print_presets():
    print("\nVerfügbare Lack-Presets:")
    for key, res in PRESET_RESISTS.items():
        print(f" - {key}: Viskosität={res.viscosity_mPa_s} mPa·s, K={res.k_factor}")


def main():
    print("=== Spin-Coating Approximation Tool (Under Development) ===")
    print_presets()

    preset_key = input("\nWähle ein Preset (z.B. 'AZ 1512') oder drücke Enter für manuell: ").strip()

    if preset_key in PRESET_RESISTS:
        resist = PRESET_RESISTS[preset_key]
        print(f"Verwende Preset: {resist.name}")
    else:
        print("\n--- Manuelle Lack-Eingabe ---")
        try:
            name = input("Lackname: ").strip() or "Custom Lack"
            visc = float(input("Viskosität (mPa·s): "))
            solid = float(input("Feststoffanteil (0.0 - 1.0): "))
            k_fac = float(input("Empirischer K-Faktor (z.B. 5000): "))
            resist = ResistProperties(
                name=name,
                viscosity_mPa_s=visc,
                solid_content_fraction=solid,
                k_factor=k_fac
            )
        except ValueError:
            print("❌ Ungültige Eingabe.")
            sys.exit(1)

    print("\nWas möchtest du berechnen?")
    print("1: Schichtdicke aus Drehzahl (rpm) berechnen")
    print("2: Benötigte Drehzahl (rpm) aus Ziel-Schichtdicke berechnen")
    choice = input("Option (1/2): ").strip()

    if choice == "1":
        rpm = float(input("Gibe die Drehzahl ein (rpm, z.B. 3000): "))
        thickness = SpinCoatingCalculator.calculate_thickness(rpm, resist)
        print(f"\n✅ Erwartete Schichtdicke für {resist.name} bei {rpm} rpm:")
        print(f"👉 {thickness} nm ({thickness / 1000.0:.3f} µm)")

    elif choice == "2":
        target_nm = float(input("Gib die Wunsch-Schichtdicke ein (nm, z.B. 500): "))
        rpm = SpinCoatingCalculator.calculate_required_rpm(target_nm, resist)
        print(f"\n✅ Benötigte Drehzahl für {resist.name} bei {target_nm} nm Schichtdicke:")
        print(f"👉 {rpm} rpm")
    else:
        print("Ungültige Option.")


if __name__ == "__main__":
    main()
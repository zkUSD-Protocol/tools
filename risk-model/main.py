from services.simulation import Simulation


def main():
    print("Starting Risk Model Simulation...")

    # Create and run simulation
    sim = Simulation()
    sim.run()

    print("\nSimulation Complete!")


if __name__ == "__main__":
    main()

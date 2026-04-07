from nostalgia_visualizer import launch_live_visualizer, list_live_input_devices


def main() -> None:
    print("Available input devices:")
    for row in list_live_input_devices():
        print(row)

    launch_live_visualizer(
        config_path="visualizer.toml",
        input_device=None,  # Use default input device.
        width=1280,
        height=720,
    )


if __name__ == "__main__":
    main()

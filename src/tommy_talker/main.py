#!/usr/bin/env python3
"""
TommyTalker - Privacy-First Voice-to-Text
Main entry point for the macOS application.
"""

import signal
import sys
from pathlib import Path

# Initialize logging first
from tommy_talker.utils import logger

from PyQt6.QtWidgets import QApplication

from tommy_talker.utils.hardware_detect import HardwareProfile, detect_hardware
from tommy_talker.utils.permissions import check_permissions, PermissionStatus
from tommy_talker.utils.config import load_config, save_config, ensure_data_dirs
from tommy_talker.gui.setup_guide import SetupGuideWindow
from tommy_talker.gui.menu_bar import MenuBarApp
from tommy_talker.gui.dashboard import DashboardWindow
from tommy_talker.app_controller import AppController


# Global references to prevent garbage collection
_app_controller = None
_menu_bar = None
_dashboard = None
_onboarding = None


def main():
    """Main entry point with permission gatekeeper."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in menu bar
    app.setApplicationName("TommyTalker")

    # Allow Ctrl+C to quit (Qt event loop swallows SIGINT by default)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    
    # Ensure data directories exist
    ensure_data_dirs()
    
    # Load configuration
    config = load_config()
    
    # Initialize logging based on config
    logger.setup_logger(enabled=config.logging_enabled)
    logger.info("TommyTalker starting...")
    
    # Detect hardware tier
    hardware = detect_hardware()
    logger.info(f"Hardware: {hardware.chip_type}, {hardware.ram_gb}GB RAM → Tier {hardware.tier}")
    
    # Permission gatekeeper - check before loading main app
    perm_status = check_permissions()
    
    if not perm_status.all_granted:
        # Show setup guide and block until permissions granted
        setup = SetupGuideWindow(perm_status)
        setup.show()
        setup.permissions_granted.connect(lambda: _after_permissions(app, config, hardware))
    else:
        _after_permissions(app, config, hardware)
    
    sys.exit(app.exec())


def _after_permissions(app: QApplication, config, hardware: HardwareProfile):
    """Handle post-permission flow: onboarding or main app."""
    global _onboarding
    
    # Show onboarding wizard on first run (unless skipped)
    if not config.skip_onboarding:
        from tommy_talker.gui.onboarding import OnboardingWizard
        
        logger.info("Showing onboarding wizard")
        _onboarding = OnboardingWizard(config, hardware)
        _onboarding.setup_complete.connect(lambda updated_config: launch_main_app(app, updated_config, hardware))
        _onboarding.rejected.connect(lambda: launch_main_app(app, config, hardware))  # Skip pressed
        _onboarding.show()
    else:
        launch_main_app(app, config, hardware)


def launch_main_app(app: QApplication, config, hardware: HardwareProfile):
    """Launch the main menu bar application after permissions are granted."""
    global _app_controller, _menu_bar, _dashboard

    # Create central app controller
    _app_controller = AppController(config, hardware)

    # Initialize GUI components
    _menu_bar = MenuBarApp(config, hardware)
    _dashboard = DashboardWindow(config, hardware)

    # Wire up connections
    _wire_connections(app, _app_controller, _menu_bar, _dashboard)
    
    # Start global hotkeys
    _app_controller.start_hotkeys()
    
    # Show menu bar
    _menu_bar.show()
    
    logger.info("Application started")


def _wire_connections(app: QApplication, controller: AppController, menu_bar: MenuBarApp,
                      dashboard: DashboardWindow):
    """Wire up signal/slot connections between components."""

    # Session recording: menu button → controller
    menu_bar.session_recording_toggled_signal.connect(controller.toggle_session_recording)

    # Session recording state → menu bar UI
    controller.session_recording_changed.connect(menu_bar.set_session_recording_state)

    # Push-to-talk recording state → menu bar status text
    controller.recording_changed.connect(menu_bar.set_recording_state)

    # Unified any-recording state → menu bar icon color
    controller.any_recording_changed.connect(menu_bar.set_any_recording_state)

    # Menu bar → Dashboard (bring to front for LSUIElement apps)
    menu_bar.open_dashboard_signal.connect(dashboard.bring_to_front)

    # Dashboard → Controller
    dashboard.config_changed_signal.connect(controller.update_config)

    # Cleanup on app quit
    app.aboutToQuit.connect(controller.shutdown)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
TommyTalker - Privacy-First Voice Intelligence Suite
Main entry point for the macOS application.
"""

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
from tommy_talker.gui.hud import HUDOverlay
from tommy_talker.app_controller import AppController
from tommy_talker.engine.modes import OperatingMode


# Global references to prevent garbage collection
_app_controller = None
_menu_bar = None
_dashboard = None
_hud = None
_onboarding = None


def main():
    """Main entry point with permission gatekeeper."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in menu bar
    app.setApplicationName("TommyTalker")
    
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
    global _app_controller, _menu_bar, _dashboard, _hud
    
    # Create central app controller
    _app_controller = AppController(config, hardware)
    
    # Initialize GUI components
    _menu_bar = MenuBarApp(config, hardware)
    _dashboard = DashboardWindow(config, hardware)
    _hud = HUDOverlay()
    
    # Wire up connections
    _wire_connections(app, _app_controller, _menu_bar, _dashboard, _hud)
    
    # Start global hotkeys
    _app_controller.start_hotkeys()
    
    # Show menu bar
    _menu_bar.show()
    
    logger.info("Application started")


def _wire_connections(app: QApplication, controller: AppController, menu_bar: MenuBarApp, 
                      dashboard: DashboardWindow, hud: HUDOverlay):
    """Wire up signal/slot connections between components."""
    
    # Menu bar → Controller
    def on_menu_mode_changed(mode_str: str):
        try:
            mode = OperatingMode(mode_str)
            controller.set_mode(mode)
        except ValueError:
            print(f"[Main] Unknown mode: {mode_str}")
    
    menu_bar.mode_changed_signal.connect(on_menu_mode_changed)
    menu_bar.recording_toggled_signal.connect(lambda _: controller.toggle_recording())
    
    # Menu bar → Dashboard
    menu_bar.open_dashboard_signal.connect(dashboard.show)
    
    # Dashboard → Controller
    dashboard.config_changed_signal.connect(controller.update_config)
    dashboard.clear_session_signal.connect(controller.clear_session)
    
    # Dashboard mode activation → Controller
    def on_dashboard_mode_activated(mode_str: str):
        try:
            mode = OperatingMode(mode_str)
            controller.set_mode(mode)
            menu_bar.update_mode(mode_str)  # Sync menu bar
        except ValueError:
            print(f"[Main] Unknown mode from dashboard: {mode_str}")
    
    dashboard.mode_activated_signal.connect(on_dashboard_mode_activated)
    
    # Controller recording state → Menu bar icon
    controller.recording_changed.connect(menu_bar.set_recording_state)
    
    # Controller → HUD (for live text in HUD mode)
    controller.live_text_updated.connect(hud.update_transcript)
    
    # Handle mode changes for HUD visibility and sync UI
    def on_mode_changed(mode: str):
        if mode == "hud":
            hud.show()
        else:
            hud.hide()
        dashboard.update_mode(mode)  # Sync dashboard
    
    controller.mode_changed.connect(on_mode_changed)
    
    # Cleanup on app quit
    app.aboutToQuit.connect(controller.shutdown)


if __name__ == "__main__":
    main()

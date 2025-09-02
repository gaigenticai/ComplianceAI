"""
UI Configuration System for ComplianceAI
Provides configurable design tokens and theme settings
Following Rule 1: No hardcoded values
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class UIThemeConfig:
    """
    UI Theme Configuration Class
    Centralizes all design tokens and theme settings
    """
    
    # Brand Colors - Configurable via environment
    brand_primary_50: str = os.getenv('UI_PRIMARY_50', '#f0f4ff')
    brand_primary_100: str = os.getenv('UI_PRIMARY_100', '#e0e7ff')
    brand_primary_200: str = os.getenv('UI_PRIMARY_200', '#c7d2fe')
    brand_primary_300: str = os.getenv('UI_PRIMARY_300', '#a5b4fc')
    brand_primary_400: str = os.getenv('UI_PRIMARY_400', '#818cf8')
    brand_primary_500: str = os.getenv('UI_PRIMARY_500', '#6366f1')
    brand_primary_600: str = os.getenv('UI_PRIMARY_600', '#4f46e5')
    brand_primary_700: str = os.getenv('UI_PRIMARY_700', '#4338ca')
    brand_primary_800: str = os.getenv('UI_PRIMARY_800', '#3730a3')
    brand_primary_900: str = os.getenv('UI_PRIMARY_900', '#312e81')
    
    # Typography - Configurable
    brand_font_family: str = os.getenv('UI_FONT_FAMILY', 'Inter')
    brand_font_mono: str = os.getenv('UI_FONT_MONO', 'JetBrains Mono')
    
    # Layout - Configurable
    container_max_width: str = os.getenv('UI_CONTAINER_WIDTH', '1280px')
    header_height: str = os.getenv('UI_HEADER_HEIGHT', '4rem')
    nav_height: str = os.getenv('UI_NAV_HEIGHT', '3.5rem')
    
    # Animation - Configurable
    transition_fast: str = os.getenv('UI_TRANSITION_FAST', '150ms')
    transition_base: str = os.getenv('UI_TRANSITION_BASE', '250ms')
    transition_slow: str = os.getenv('UI_TRANSITION_SLOW', '350ms')
    
    # Component Settings - Configurable
    card_border_radius: str = os.getenv('UI_CARD_RADIUS', '1rem')
    button_border_radius: str = os.getenv('UI_BUTTON_RADIUS', '0.5rem')
    input_border_radius: str = os.getenv('UI_INPUT_RADIUS', '0.5rem')
    
    # Dashboard Specific - Configurable
    dashboard_title: str = os.getenv('UI_DASHBOARD_TITLE', 'ComplianceAI Intelligence')
    dashboard_subtitle: str = os.getenv('UI_DASHBOARD_SUBTITLE', 'Advanced KYC Processing & Compliance Automation Platform')
    company_name: str = os.getenv('UI_COMPANY_NAME', 'ComplianceAI')
    
    def to_css_variables(self) -> str:
        """
        Generate CSS custom properties from configuration
        Returns CSS variables that can be injected into templates
        """
        return f"""
        :root {{
            /* Brand Colors */
            --brand-primary-50: {self.brand_primary_50};
            --brand-primary-100: {self.brand_primary_100};
            --brand-primary-200: {self.brand_primary_200};
            --brand-primary-300: {self.brand_primary_300};
            --brand-primary-400: {self.brand_primary_400};
            --brand-primary-500: {self.brand_primary_500};
            --brand-primary-600: {self.brand_primary_600};
            --brand-primary-700: {self.brand_primary_700};
            --brand-primary-800: {self.brand_primary_800};
            --brand-primary-900: {self.brand_primary_900};
            
            /* Typography */
            --brand-font-family: '{self.brand_font_family}';
            --brand-font-mono: '{self.brand_font_mono}';
            
            /* Layout */
            --container-max-width: {self.container_max_width};
            --header-height: {self.header_height};
            --nav-height: {self.nav_height};
            
            /* Animation */
            --transition-fast: {self.transition_fast};
            --transition-base: {self.transition_base};
            --transition-slow: {self.transition_slow};
            
            /* Components */
            --card-border-radius: {self.card_border_radius};
            --button-border-radius: {self.button_border_radius};
            --input-border-radius: {self.input_border_radius};
        }}
        """
    
    def to_template_context(self) -> Dict[str, Any]:
        """
        Generate template context variables
        Returns dictionary for template rendering
        """
        return {
            'dashboard_title': self.dashboard_title,
            'dashboard_subtitle': self.dashboard_subtitle,
            'company_name': self.company_name,
            'brand_colors': {
                'primary_600': self.brand_primary_600,
                'primary_700': self.brand_primary_700,
            },
            'fonts': {
                'family': self.brand_font_family,
                'mono': self.brand_font_mono,
            },
            'layout': {
                'container_width': self.container_max_width,
                'header_height': self.header_height,
                'nav_height': self.nav_height,
            }
        }


# Global UI configuration instance
ui_config = UIThemeConfig()


def get_ui_config() -> UIThemeConfig:
    """
    Get the global UI configuration instance
    
    Returns:
        UIThemeConfig: The configured UI theme settings
    """
    return ui_config


def update_ui_config(**kwargs) -> None:
    """
    Update UI configuration at runtime
    
    Args:
        **kwargs: Configuration values to update
    """
    global ui_config
    for key, value in kwargs.items():
        if hasattr(ui_config, key):
            setattr(ui_config, key, value)


def get_css_variables() -> str:
    """
    Get CSS variables for the current UI configuration
    
    Returns:
        str: CSS custom properties string
    """
    return ui_config.to_css_variables()


def get_template_context() -> Dict[str, Any]:
    """
    Get template context for the current UI configuration
    
    Returns:
        Dict[str, Any]: Template context variables
    """
    return ui_config.to_template_context()

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe


register = template.Library()


ICON_PATHS = {
    'sparkles': '''
        <path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/>
        <path d="M19 3l.8 2.2L22 6l-2.2.8L19 9l-.8-2.2L16 6l2.2-.8z"/>
        <path d="M5 15l1 2.5L8.5 18 6 19l-1 2.5L4 19l-2.5-1 2.5-.5z"/>
    ''',
    'layout-grid': '''
        <rect x="3" y="3" width="7" height="7" rx="1.5"/>
        <rect x="14" y="3" width="7" height="7" rx="1.5"/>
        <rect x="3" y="14" width="7" height="7" rx="1.5"/>
        <rect x="14" y="14" width="7" height="7" rx="1.5"/>
    ''',
    'folder-up': '''
        <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
        <path d="M12 17V10"/>
        <path d="M9.5 12.5 12 10l2.5 2.5"/>
    ''',
    'activity': '''
        <path d="M3 12h4l2-5 4 10 2-5h6"/>
    ''',
    'shield': '''
        <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/>
    ''',
    'workflow': '''
        <rect x="3" y="4" width="6" height="6" rx="1.5"/>
        <rect x="15" y="4" width="6" height="6" rx="1.5"/>
        <rect x="9" y="14" width="6" height="6" rx="1.5"/>
        <path d="M9 7h6M12 10v4"/>
    ''',
    'square-terminal': '''
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M8 9l3 3-3 3"/>
        <path d="M13 15h3"/>
    ''',
    'save': '''
        <path d="M5 4h11l3 3v13H5z"/>
        <path d="M8 4v6h8V4"/>
        <path d="M8 20v-6h8v6"/>
    ''',
    'search': '''
        <circle cx="11" cy="11" r="6"/>
        <path d="M20 20l-4.2-4.2"/>
    ''',
    'pencil': '''
        <path d="M4 20l4.5-1 9-9-3.5-3.5-9 9z"/>
        <path d="M13.5 6.5 17 10"/>
    ''',
    'cpu': '''
        <rect x="7" y="7" width="10" height="10" rx="2"/>
        <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 15h3M1 9h3M1 15h3"/>
        <rect x="10" y="10" width="4" height="4" rx="1"/>
    ''',
    'wallet': '''
        <path d="M4 7h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4z"/>
        <path d="M4 7V6a2 2 0 0 1 2-2h11"/>
        <circle cx="16" cy="13" r="1"/>
    ''',
    'briefcase': '''
        <rect x="3" y="7" width="18" height="12" rx="2"/>
        <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/>
        <path d="M3 12h18"/>
    ''',
    'settings-2': '''
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a2 2 0 1 1-4 0v-.2a1 1 0 0 0-.7-.9 1 1 0 0 0-1.1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a2 2 0 1 1 0-4h.2a1 1 0 0 0 .9-.7 1 1 0 0 0-.2-1.1l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1 1 0 0 0 1.1.2H9a1 1 0 0 0 .6-.9V4a2 2 0 1 1 4 0v.2a1 1 0 0 0 .7.9 1 1 0 0 0 1.1-.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1 1 0 0 0-.2 1.1V9c0 .4.2.7.6.9H20a2 2 0 1 1 0 4h-.2a1 1 0 0 0-.9.7z"/>
    ''',
    'file-code-2': '''
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>
        <path d="M14 3v5h5"/>
        <path d="M10 13l-2 2 2 2M14 13l2 2-2 2"/>
    ''',
    'shield-check': '''
        <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/>
        <path d="M9 12l2 2 4-4"/>
    ''',
}


def _svg_markup(icon_name, classes='h-5 w-5'):
    body = ICON_PATHS.get(icon_name) or ICON_PATHS['sparkles']
    return format_html(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        'stroke-linejoin="round" class="{}">{}</svg>',
        classes,
        mark_safe(body),
    )


@register.simple_tag
def app_icon(icon_name, classes='h-5 w-5'):
    return _svg_markup(icon_name or 'sparkles', classes)

/**
 * ThemeScript purges obsolete theme preferences from localStorage
 * and guarantees permanent dark mode attributes.
 */
export function ThemeScript() {
  const purgeScript = `
    (function() {
      try {
        localStorage.removeItem('credlab-theme');
        document.documentElement.setAttribute('data-theme', 'dark');
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
        document.documentElement.style.colorScheme = 'dark';
      } catch (e) {}
    })();
  `;

  return (
    <script
      id="credlab-theme-purge"
      dangerouslySetInnerHTML={{ __html: purgeScript }}
      suppressHydrationWarning
    />
  );
}

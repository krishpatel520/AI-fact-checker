/** Spinner.jsx — animated SVG loading spinner */
export function Spinner({ size = 20, color = '#818cf8' }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
            className="spinner" style={{ minWidth: size }}>
            <circle cx="12" cy="12" r="10" stroke={color + '33'} strokeWidth="3" />
            <path d="M12 2 A10 10 0 0 1 22 12" stroke={color} strokeWidth="3" strokeLinecap="round" />
        </svg>
    )
}

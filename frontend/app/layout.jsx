import "./globals.css"

export const metadata = {
  title: "SCM Recommendation | SmartTrace",
  description: "SCM Recommendation | SmartTrace"
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        {children}
      </body>
    </html>
  )
}

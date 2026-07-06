import "./globals.css"

export const metadata = {
  title: "SCM Recommendation | SmartTrace",
  description: "SCM Recommendation | SmartTrace"
}

import Navbar from "./components/Navbar"

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen flex flex-col">
        <Navbar />
        {children}
      </body>
    </html>
  )
}

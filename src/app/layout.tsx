import React from 'react'
import { Outlet } from 'react-router-dom'
import { ThemeProvider } from "src/libs/theme-provider"

function Layout() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <div className="light:bg-white light:text-gray-900">
        <Outlet />
      </div>
    </ThemeProvider>
  );
}

export default Layout
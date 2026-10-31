import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import CreateStaffModal from "../common/CreateStaffModal";

export function AppLayout({ currentPath, onNavigate, currentTitle, children }) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCreateStaffOpen, setIsCreateStaffOpen] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <Sidebar
        currentPath={currentPath}
        onNavigate={onNavigate}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
        onOpenCreateStaff={() => setIsCreateStaffOpen(true)}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Navbar
          onOpenMobile={() => setIsMobileOpen(true)}
          currentTitle={currentTitle}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
      </div>

      {/* Admin Create Staff Modal */}
      <CreateStaffModal
        isOpen={isCreateStaffOpen}
        onClose={() => setIsCreateStaffOpen(false)}
      />
    </div>
  );
}

export default AppLayout;

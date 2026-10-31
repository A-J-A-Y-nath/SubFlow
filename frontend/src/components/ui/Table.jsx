import React from "react";
import { cn } from "../../lib/utils";

export function Table({ className, children, ...props }) {
  return (
    <div className="relative w-full overflow-auto rounded-lg border border-slate-800">
      <table className={cn("w-full caption-bottom text-sm", className)} {...props}>
        {children}
      </table>
    </div>
  );
}

export function TableHeader({ className, children, ...props }) {
  return (
    <thead className={cn("bg-slate-900/90 border-b border-slate-800", className)} {...props}>
      {children}
    </thead>
  );
}

export function TableBody({ className, children, ...props }) {
  return (
    <tbody className={cn("divide-y divide-slate-800/60 bg-slate-900/30", className)} {...props}>
      {children}
    </tbody>
  );
}

export function TableRow({ className, children, ...props }) {
  return (
    <tr
      className={cn(
        "transition-colors hover:bg-slate-800/40 data-[state=selected]:bg-slate-800",
        className
      )}
      {...props}
    >
      {children}
    </tr>
  );
}

export function TableHead({ className, children, ...props }) {
  return (
    <th
      className={cn(
        "h-10 px-4 text-left align-middle text-xs font-semibold text-slate-400 uppercase tracking-wider",
        className
      )}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableCell({ className, children, ...props }) {
  return (
    <td className={cn("p-4 align-middle text-slate-200 text-sm", className)} {...props}>
      {children}
    </td>
  );
}

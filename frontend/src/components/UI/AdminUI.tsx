interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Card({ title, children, className = "" }: CardProps) {
  return (
    <div
      className={`bg-white rounded-card shadow-sm border border-gray-100 p-5 ${className}`}
    >
      {title && (
        <h3 className="text-base font-semibold text-gray-800 mb-4">{title}</h3>
      )}
      {children}
    </div>
  );
}

export function Loading({ text = "加载中..." }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <p className="text-gray-400 text-sm">{text}</p>
    </div>
  );
}

export function Empty({ text = "暂无数据" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <p className="text-gray-400 text-sm">{text}</p>
    </div>
  );
}

export function ErrorText({ text }: { text: string }) {
  if (!text) return null;
  return <p className="text-coral text-sm mt-2">{text}</p>;
}

export function SuccessText({ text }: { text: string }) {
  if (!text) return null;
  return <p className="text-green-600 text-sm mt-2">{text}</p>;
}

export function Badge({
  children,
  color = "gray",
}: {
  children: React.ReactNode;
  color?: "gray" | "green" | "coral" | "blue" | "amber";
}) {
  const colors: Record<string, string> = {
    gray: "bg-gray-100 text-gray-600",
    green: "bg-green-50 text-green-700",
    coral: "bg-coral/10 text-coral",
    blue: "bg-blue-50 text-blue-700",
    amber: "bg-amber-50 text-amber-700",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${colors[color]}`}
    >
      {children}
    </span>
  );
}

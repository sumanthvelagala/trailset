import React from "react";
import TripForm from "@/components/TripForm";
import Image from "next/image";

interface PhotoItem {
  src: string;
  location: string;
  state: string;
  width: number;
  height: number;
  rotate: string;
  pos: string;
  style?: React.CSSProperties;
  show: string;
}

const photos: PhotoItem[] = [
  // Corners
  {
    src: "https://images.unsplash.com/photo-1474044159687-1ee9f3a51722?w=600&q=90",
    location: "Grand Canyon", state: "AZ",
    width: 185, height: 225,
    rotate: "rotate-4",
    pos: "",
    style: { top: "10%", left: "20%" },
    show: "block",
  },
  {
    src: "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=600&q=90",
    location: "Golden Gate", state: "CA",
    width: 190, height: 135,
    rotate: "-rotate-2",
    pos: "",
    style: { bottom: "10%", right: "20%" },
    show: "block",
  },
  {
    src: "https://images.unsplash.com/photo-1534430480872-3498386e7856?w=600&q=90",
    location: "New York City", state: "NY",
    width: 150, height: 200,
    rotate: "-rotate-4",
    pos: "",
    style: { top: "-1%", right: "-1%" },
    show: "hidden lg:block",
  },
  {
    src: "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=600&q=90",
    location: "Chicago", state: "IL",
    width: 205, height: 150,
    rotate: "rotate-2",
    pos: "",
    style: { bottom: "4%", left: "5%" },
    show: "hidden lg:block",
  },
  {
    src: "https://images.unsplash.com/photo-1472396961693-142e6e269027?w=600&q=90",
    location: "Yosemite", state: "CA",
    width: 165, height: 215,
    rotate: "-rotate-3",
    pos: "",
    style: { top: "40%", left: "2%" },
    show: "hidden xl:block",
  },
  {
    src: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&q=90",
    location: "Rocky Mountains", state: "CO",
    width: 200, height: 140,
    rotate: "rotate-5",
    pos: "",
    style: { bottom: "25%", left: "25%" },
    show: "hidden xl:block",
  },
  {
    src: "https://images.unsplash.com/photo-1570197571499-166b36435e9f?w=600&q=90",
    location: "New Orleans", state: "LA",
    width: 180, height: 230,
    rotate: "rotate-2",
    pos: "",
    style: { top: "26%", right: "10%" },
    show: "hidden xl:block",
  },
  {
    src: "https://images.unsplash.com/photo-1546436836-07a91091f160?w=600&q=90",
    location: "Manhattan", state: "NY",
    width: 200, height: 145,
    rotate: "-rotate-3",
    pos: "",
    style: { bottom: "30%", right: "3%" },
    show: "hidden xl:block",
  },
];

function PolaroidPhoto({ photo }: { photo: PhotoItem }) {
  return (
    <div
      className={`pointer-events-none absolute ${photo.pos} ${photo.rotate} ${photo.show}`}
      style={{ zIndex: 0, ...photo.style }}
    >
      <div
        style={{
          background: "white",
          padding: "7px 7px 0 7px",
          boxShadow: "0 4px 20px rgba(0,0,0,0.13), 0 1px 6px rgba(0,0,0,0.07)",
        }}
      >
        <div style={{ position: "relative", width: photo.width, height: photo.height }}>
          <Image
            src={photo.src}
            alt={`${photo.location}, ${photo.state}`}
            fill
            className="object-cover"
          />
        </div>
        <div className="py-2 px-1 flex items-center gap-1">
          <svg width="9" height="9" viewBox="0 0 24 24" fill="#E8445A" className="shrink-0">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
          </svg>
          <span className="text-xs font-medium text-gray-700 whitespace-nowrap">{photo.location}</span>
          <span className="text-xs text-gray-400">· {photo.state}</span>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <main
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-4 py-16 gap-8"
      style={{ background: "var(--background)" }}
    >
      {/* Scattered polaroid photos — behind everything */}
      {photos.map((photo) => (
        <PolaroidPhoto key={`${photo.location}-${photo.state}`} photo={photo} />
      ))}

      {/* Headline — above form, on top of photos */}
      <div className="relative z-10 text-center max-w-xl">
        <h1
          className="text-5xl font-bold tracking-tight leading-tight mb-3"
          style={{ color: "var(--foreground)" }}
        >
          Where are we<br />wandering?
        </h1>
        <p className="text-lg" style={{ color: "var(--muted)" }}>
          Give us a city, a date, and a budget. We'll stitch together a day that fits your vibe.
        </p>
      </div>

      {/* Form card — always on top */}
      <div className="relative z-10 w-full max-w-xl bg-white rounded-2xl shadow-lg shadow-gray-200/80 px-8 py-10">
        <TripForm />
      </div>
    </main>
  );
}

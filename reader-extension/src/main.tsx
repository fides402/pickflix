import React from "react";
import ReactDOM from "react-dom/client";

import "@fontsource/literata/400.css";
import "@fontsource/literata/500.css";
import "@fontsource/literata/600.css";
import "@fontsource/literata/700.css";
import "@fontsource/source-serif-4/400.css";
import "@fontsource/source-serif-4/500.css";
import "@fontsource/source-serif-4/600.css";
import "@fontsource/source-serif-4/700.css";
import "@fontsource/lora/400.css";
import "@fontsource/lora/500.css";
import "@fontsource/lora/600.css";
import "@fontsource/lora/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";

import "./styles/reader.css";
import { ReaderApp } from "./app/ReaderApp";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ReaderApp />
  </React.StrictMode>,
);

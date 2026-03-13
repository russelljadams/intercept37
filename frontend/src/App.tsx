import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Traffic from "./pages/Traffic";
import Repeater from "./pages/Repeater";
import Scanner from "./pages/Scanner";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="traffic" element={<Traffic />} />
        <Route path="repeater" element={<Repeater />} />
        <Route path="scanner" element={<Scanner />} />
      </Route>
    </Routes>
  );
}

import { useState, useRef } from "react";
import jsPDF from "jspdf";
import QRCode from "qrcode";

import {
    askAI,
    searchTrains,
    getRealtime,
    getSeats,
    bookTicket,
} from "./api";

import "./App.css";

function App() {
    const bookingRef = useRef(null);

    const [query, setQuery] = useState("");
    const [aiAnswer, setAiAnswer] = useState("");
    const [aiLoading, setAiLoading] = useState(false);

    const [filters, setFilters] = useState({
        from_city: "",
        to_city: "",
        date: "",
        provider: "",
        sort_by: "best",
        passenger_type: "regular",
        direct_only: false,
        wifi: false,
        available_only: false,
    });

    const [trains, setTrains] = useState([]);
    const [searchLoading, setSearchLoading] = useState(false);

    const [city, setCity] = useState("");
    const [departures, setDepartures] = useState([]);
    const [liveLoading, setLiveLoading] = useState(false);

    const [selectedTrain, setSelectedTrain] = useState(null);
    const [seats, setSeats] = useState([]);
    const [selectedSeats, setSelectedSeats] = useState([]);
    const [passengerNames, setPassengerNames] = useState({});
    const [tickets, setTickets] = useState([]);
    const [bookingLoading, setBookingLoading] = useState(false);

    function handleFilterChange(e) {
        const { name, value, type, checked } = e.target;

        setFilters({
            ...filters,
            [name]: type === "checkbox" ? checked : value,
        });
    }

    async function handleAsk(e) {
        e.preventDefault();

        try {
            setAiLoading(true);
            setAiAnswer("");

            const data = await askAI(query);
            setAiAnswer(data.answer || "No answer returned.");
        } catch (error) {
            console.error(error);
            setAiAnswer(
                "Backend error. Make sure FastAPI is running on http://127.0.0.1:8000"
            );
        } finally {
            setAiLoading(false);
        }
    }

    async function handleSearch(e) {
        e.preventDefault();

        try {
            setSearchLoading(true);
            setSelectedTrain(null);
            setTickets([]);

            const data = await searchTrains(filters);
            setTrains(data || []);
        } catch (error) {
            console.error(error);
            alert("Search failed. Check backend.");
        } finally {
            setSearchLoading(false);
        }
    }

    async function handleRealtime(e) {
        e.preventDefault();

        try {
            setLiveLoading(true);
            const data = await getRealtime(city);
            setDepartures(data.departures || []);
        } catch (error) {
            console.error(error);
            alert("Realtime API failed. Check backend.");
        } finally {
            setLiveLoading(false);
        }
    }

    async function handleSelectTrain(train) {
        try {
            setSelectedTrain(train);
            setTickets([]);
            setSelectedSeats([]);
            setPassengerNames({});

            const data = await getSeats(train.route_id);
            setSeats(data || []);

            setTimeout(() => {
                bookingRef.current?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
            }, 150);
        } catch (error) {
            console.error(error);
            alert("Could not load seats.");
        }
    }

    function handleSeatToggle(seat) {
        if (!seat.available) return;

        if (selectedSeats.includes(seat.seat_number)) {
            const updatedSeats = selectedSeats.filter((s) => s !== seat.seat_number);
            const updatedNames = { ...passengerNames };
            delete updatedNames[seat.seat_number];

            setSelectedSeats(updatedSeats);
            setPassengerNames(updatedNames);
        } else {
            setSelectedSeats([...selectedSeats, seat.seat_number]);
        }
    }

    function handlePassengerNameChange(seatNumber, name) {
        setPassengerNames({
            ...passengerNames,
            [seatNumber]: name,
        });
    }

    function getSelectedPrice(train) {
        if (!train) return 0;

        if (filters.passenger_type === "senior") return train.senior_price;
        if (filters.passenger_type === "youth") return train.youth_price;
        if (filters.passenger_type === "child") return train.child_price;

        return train.base_price;
    }

    async function handleBookTicket() {
        if (!selectedTrain) {
            alert("Please select a train.");
            return;
        }

        if (selectedSeats.length === 0) {
            alert("Please select at least one seat.");
            return;
        }

        for (const seat of selectedSeats) {
            if (!passengerNames[seat] || passengerNames[seat].trim() === "") {
                alert(`Please enter passenger name for seat ${seat}.`);
                return;
            }
        }

        try {
            setBookingLoading(true);

            const createdTickets = [];

            for (const seatNumber of selectedSeats) {
                const result = await bookTicket({
                    route_id: selectedTrain.route_id,
                    train_name: selectedTrain.train_name,
                    passenger_name: passengerNames[seatNumber],
                    passenger_type: filters.passenger_type,
                    seat_number: seatNumber,
                    price: Number(getSelectedPrice(selectedTrain)),
                });

                if (result.success) {
                    createdTickets.push(result.ticket);
                } else {
                    alert(result.message || `Booking failed for seat ${seatNumber}`);
                }
            }

            if (createdTickets.length > 0) {
                setTickets(createdTickets);

                const updatedSeats = await getSeats(selectedTrain.route_id);
                setSeats(updatedSeats || []);
                setSelectedSeats([]);
                setPassengerNames({});

                setTimeout(() => {
                    window.scrollTo({
                        top: document.body.scrollHeight,
                        behavior: "smooth",
                    });
                }, 150);
            }
        } catch (error) {
            console.error(error);
            alert("Booking failed. Check backend.");
        } finally {
            setBookingLoading(false);
        }
    }

    async function downloadTicketPDF(ticket) {
        const doc = new jsPDF();

        const qrText = `
EuroRail Ticket
PNR: ${ticket.pnr}
Booking ID: ${ticket.booking_id}
Passenger: ${ticket.passenger_name}
Passenger Type: ${ticket.passenger_type}
Train: ${ticket.train_name}
Seat: ${ticket.seat_number}
Price: ${ticket.price} ${ticket.currency}
Status: ${ticket.status}
Booking Time: ${ticket.booking_time}
`;

        const qrImage = await QRCode.toDataURL(qrText);

        doc.setFontSize(22);
        doc.text("EuroRail Ticket", 20, 20);

        doc.setFontSize(12);
        doc.text(`Booking ID: ${ticket.booking_id}`, 20, 40);
        doc.text(`PNR: ${ticket.pnr}`, 20, 50);
        doc.text(`Passenger: ${ticket.passenger_name}`, 20, 60);
        doc.text(`Passenger Type: ${ticket.passenger_type}`, 20, 70);
        doc.text(`Train: ${ticket.train_name}`, 20, 80);
        doc.text(`Seat: ${ticket.seat_number}`, 20, 90);
        doc.text(`Price: ${ticket.price} ${ticket.currency}`, 20, 100);
        doc.text(`Status: ${ticket.status}`, 20, 110);
        doc.text(`Booking Time: ${ticket.booking_time}`, 20, 120);

        doc.text("Scan QR for ticket verification", 20, 140);
        doc.addImage(qrImage, "PNG", 20, 150, 55, 55);

        doc.save(`${ticket.pnr}_ticket.pdf`);
    }

    function renderSeat(seat, type) {
        if (!seat) return <div className="seat-placeholder"></div>;

        const isSelected = selectedSeats.includes(seat.seat_number);

        return (
            <button
                key={seat.seat_number}
                className={
                    seat.available
                        ? isSelected
                            ? `seat selected ${type}`
                            : `seat ${type}`
                        : `seat booked ${type}`
                }
                disabled={!seat.available}
                onClick={() => handleSeatToggle(seat)}
                title={`${seat.seat_number} - ${type}`}
            >
                {seat.seat_number}
            </button>
        );
    }

    return (
        <div className="page">
            <div className="hero">
                <h1>🚆 EuroRail Live AI Assistant</h1>
                <p>
                    Search trains, compare fares, check live departures, select seats, and
                    generate tickets.
                </p>
            </div>

            <section className="panel">
                <h2>Ask AI</h2>

                <form onSubmit={handleAsk} className="row">
                    <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Example: Is SNCF available from Paris to Berlin?"
                        required
                    />
                    <button type="submit">{aiLoading ? "Thinking..." : "Ask"}</button>
                </form>

                {aiAnswer && (
                    <div className="answer-box">
                        <h3>AI Answer</h3>
                        <pre>{aiAnswer}</pre>
                    </div>
                )}
            </section>

            <section className="panel">
                <h2>Search Trains</h2>

                <form onSubmit={handleSearch} className="filters">
                    <input
                        name="from_city"
                        placeholder="From city"
                        value={filters.from_city}
                        onChange={handleFilterChange}
                    />

                    <input
                        name="to_city"
                        placeholder="To city"
                        value={filters.to_city}
                        onChange={handleFilterChange}
                    />

                    <input
                        name="date"
                        placeholder="Date: 2026-05-10"
                        value={filters.date}
                        onChange={handleFilterChange}
                    />

                    <input
                        name="provider"
                        placeholder="Provider: SNCF / DB / Eurostar"
                        value={filters.provider}
                        onChange={handleFilterChange}
                    />

                    <select
                        name="sort_by"
                        value={filters.sort_by}
                        onChange={handleFilterChange}
                    >
                        <option value="best">Best</option>
                        <option value="cheapest">Cheapest</option>
                        <option value="fastest">Fastest</option>
                        <option value="available">Most Seats</option>
                        <option value="least_delay">Least Delay</option>
                    </select>

                    <select
                        name="passenger_type"
                        value={filters.passenger_type}
                        onChange={handleFilterChange}
                    >
                        <option value="regular">Regular</option>
                        <option value="senior">Senior</option>
                        <option value="youth">Youth</option>
                        <option value="child">Child</option>
                    </select>

                    <label className="check">
                        <input
                            type="checkbox"
                            name="direct_only"
                            checked={filters.direct_only}
                            onChange={handleFilterChange}
                        />
                        Direct
                    </label>

                    <label className="check">
                        <input
                            type="checkbox"
                            name="wifi"
                            checked={filters.wifi}
                            onChange={handleFilterChange}
                        />
                        WiFi
                    </label>

                    <label className="check">
                        <input
                            type="checkbox"
                            name="available_only"
                            checked={filters.available_only}
                            onChange={handleFilterChange}
                        />
                        Available
                    </label>

                    <button type="submit">
                        {searchLoading ? "Searching..." : "Search"}
                    </button>
                </form>

                <div className="cards">
                    {trains.length === 0 && (
                        <p className="empty">No train results yet. Try Paris → Berlin.</p>
                    )}

                    {trains.map((train, index) => (
                        <div className="card" key={train.route_id || index}>
                            <div className="card-top">
                                <h3>{train.train_name}</h3>

                                <div className="badges">
                                    <span className="badge provider">{train.provider}</span>

                                    {train.provider?.includes("+") ? (
                                        <span className="badge multi">Multi-provider</span>
                                    ) : (
                                        <span className="badge direct">Single provider</span>
                                    )}

                                    {train.status === "Available" && (
                                        <span className="badge available">Available</span>
                                    )}

                                    {train.status === "Sold Out" && (
                                        <span className="badge sold">Sold Out</span>
                                    )}

                                    {train.status === "Cancelled" && (
                                        <span className="badge cancelled">Cancelled</span>
                                    )}

                                    {Number(train.delay_minutes) > 0 && (
                                        <span className="badge delay">Delayed</span>
                                    )}
                                </div>
                            </div>

                            <p className="route">
                                {train.from_city} → {train.to_city}
                            </p>

                            <div className="grid">
                                <p><b>Date:</b> {train.date}</p>
                                <p><b>Time:</b> {train.departure_time} → {train.arrival_time}</p>
                                <p><b>Duration:</b> {train.duration}</p>
                                <p>
                                    <b>Journey:</b>{" "}
                                    {train.provider?.includes("+")
                                        ? "Connection (Multi-provider)"
                                        : train.journey_type}
                                </p>
                                <p><b>Connection:</b> {train.connection_city}</p>
                                <p><b>Status:</b> {train.status}</p>
                                <p><b>Seats:</b> {train.available_seats}/{train.total_seats}</p>
                                <p><b>Base:</b> {train.base_price} {train.currency}</p>
                                <p><b>Senior:</b> {train.senior_price} {train.currency}</p>
                                <p><b>Youth:</b> {train.youth_price} {train.currency}</p>
                                <p><b>WiFi:</b> {train.wifi}</p>
                                <p><b>Delay:</b> {train.delay_minutes} min</p>
                            </div>

                            <button
                                className="select-btn"
                                onClick={() => handleSelectTrain(train)}
                                disabled={
                                    train.status === "Sold Out" ||
                                    train.status === "Cancelled" ||
                                    Number(train.available_seats) <= 0
                                }
                            >
                                Select Train
                            </button>
                        </div>
                    ))}
                </div>
            </section>

            {selectedTrain && (
                <section className="panel" ref={bookingRef}>
                    <h2>Seat Selection & Booking</h2>

                    <div className="selected-train">
                        <h3>
                            {selectedTrain.train_name} - {selectedTrain.provider}
                        </h3>
                        <p>{selectedTrain.from_city} → {selectedTrain.to_city}</p>
                        <p>
                            {selectedTrain.departure_time} → {selectedTrain.arrival_time} |{" "}
                            {selectedTrain.duration}
                        </p>
                        <p><b>Passenger type:</b> {filters.passenger_type}</p>
                        <p>
                            <b>Price per seat:</b> {getSelectedPrice(selectedTrain)}{" "}
                            {selectedTrain.currency}
                        </p>
                        <p>
                            <b>Total price:</b>{" "}
                            {selectedSeats.length * Number(getSelectedPrice(selectedTrain))}{" "}
                            {selectedTrain.currency}
                        </p>
                    </div>

                    <h3>Select Seats</h3>

                    <div className="coach-layout">
                        <div className="coach-header">
                            <span>Window</span>
                            <span>A</span>
                            <span>B</span>
                            <span>Aisle</span>
                            <span>C</span>
                            <span>D</span>
                            <span>Window</span>
                        </div>

                        {Array.from({ length: 10 }, (_, rowIndex) => {
                            const row = rowIndex + 1;

                            const seatA = seats.find((s) => s.seat_number === `${row}A`);
                            const seatB = seats.find((s) => s.seat_number === `${row}B`);
                            const seatC = seats.find((s) => s.seat_number === `${row}C`);
                            const seatD = seats.find((s) => s.seat_number === `${row}D`);

                            return (
                                <div className="coach-row" key={row}>
                                    <span className="window-label">▌</span>
                                    {renderSeat(seatA, "window-seat")}
                                    {renderSeat(seatB, "aisle-seat")}
                                    <div className="aisle-space">||</div>
                                    {renderSeat(seatC, "aisle-seat")}
                                    {renderSeat(seatD, "window-seat")}
                                    <span className="window-label">▐</span>
                                </div>
                            );
                        })}
                    </div>

                    <div className="seat-legend">
                        <span><b className="legend available"></b> Available</span>
                        <span><b className="legend selected"></b> Selected</span>
                        <span><b className="legend booked"></b> Booked</span>
                        <span><b className="legend window"></b> Window Seat</span>
                    </div>

                    <p>
                        <b>Selected Seats:</b>{" "}
                        {selectedSeats.length > 0 ? selectedSeats.join(", ") : "None"}
                    </p>

                    {selectedSeats.length > 0 && (
                        <div className="passenger-list">
                            <h3>Passenger Details</h3>

                            {selectedSeats.map((seat) => (
                                <div className="passenger-row" key={seat}>
                                    <label><b>Seat {seat}</b></label>
                                    <input
                                        value={passengerNames[seat] || ""}
                                        onChange={(e) =>
                                            handlePassengerNameChange(seat, e.target.value)
                                        }
                                        placeholder={`Passenger name for seat ${seat}`}
                                    />
                                </div>
                            ))}
                        </div>
                    )}

                    <button onClick={handleBookTicket} disabled={bookingLoading}>
                        {bookingLoading ? "Booking..." : "Confirm Booking"}
                    </button>
                </section>
            )}

            {tickets.length > 0 && (
                <section className="panel ticket">
                    <h2>🎫 Tickets Confirmed</h2>

                    {tickets.map((ticket) => (
                        <div className="ticket-box" key={ticket.booking_id}>
                            <p><b>Booking ID:</b> {ticket.booking_id}</p>
                            <p><b>PNR:</b> {ticket.pnr}</p>
                            <p><b>Passenger:</b> {ticket.passenger_name}</p>
                            <p><b>Passenger Type:</b> {ticket.passenger_type}</p>
                            <p><b>Train:</b> {ticket.train_name}</p>
                            <p><b>Seat:</b> {ticket.seat_number}</p>
                            <p><b>Price:</b> {ticket.price} {ticket.currency}</p>
                            <p><b>Status:</b> {ticket.status}</p>
                            <p><b>Booking Time:</b> {ticket.booking_time}</p>

                            <button onClick={() => downloadTicketPDF(ticket)}>
                                Download PDF Ticket
                            </button>

                            <hr />
                        </div>
                    ))}
                </section>
            )}

            <section className="panel">
                <h2>Live DB Departures</h2>

                <form onSubmit={handleRealtime} className="row">
                    <input
                        value={city}
                        onChange={(e) => setCity(e.target.value)}
                        placeholder="Berlin / Frankfurt / Munich / Hamburg / Cologne"
                        required
                    />
                    <button type="submit">
                        {liveLoading ? "Checking..." : "Check Live"}
                    </button>
                </form>

                <div className="cards">
                    {departures.map((dep, index) => (
                        <div className="card live-card" key={index}>
                            <h3>{dep.line || "Unknown Line"}</h3>
                            <p className="route">To: {dep.direction}</p>
                            <p><b>Planned:</b> {dep.planned_when}</p>
                            <p><b>Actual:</b> {dep.actual_when}</p>
                            <p><b>Delay:</b> {dep.delay} seconds</p>
                            <p><b>Platform:</b> {dep.platform}</p>
                            <p><b>Cancelled:</b> {String(dep.cancelled)}</p>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}

export default App;
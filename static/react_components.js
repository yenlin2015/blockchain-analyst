const { useState, useEffect } = React;

function Sidebar({ onHistoryItemClick }) {
    const [history, setHistory] = useState([]);

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        const response = await fetch('/get_history');
        const data = await response.json();
        setHistory(data);
    };

    return (
        <div className="sidebar">
            <h2 className="text-xl font-semibold mb-4 text-blue-400">Query History</h2>
            {history.map((item) => (
                <div key={item.id} className="history-item" onClick={() => onHistoryItemClick(item.id)}>
                    <p className="history-title">{item.report_title}</p>
                    <p className="history-date">{new Date(item.created_at).toLocaleString()}</p>
                </div>
            ))}
        </div>
    );
}

function TranscriptSummarizer() {
    const [inputType, setInputType] = useState('text');
    const [reportType, setReportType] = useState('analyst');
    const [transcript, setTranscript] = useState('');
    const [youtubeLink, setYoutubeLink] = useState('');
    const [loading, setLoading] = useState(false);
    const [analysisComplete, setAnalysisComplete] = useState(false);
    const [activeResultTab, setActiveResultTab] = useState("transcript");
    const [summary, setSummary] = useState("");
    const [chunkSummaries, setChunkSummaries] = useState([]);
    const [reportTitle, setReportTitle] = useState("");
    const [reportSubtitle, setReportSubtitle] = useState("");
    const [streamingContent, setStreamingContent] = useState([]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setAnalysisComplete(false);
        setSummary("");
        setChunkSummaries([]);
        setStreamingContent([]);
        
        const formData = new FormData();
        formData.append('input_type', inputType);
        formData.append('report_type', reportType);
        
        if (inputType === 'text') {
            formData.append('transcript', transcript);
        } else {
            formData.append('youtube_link', youtubeLink);
        }

        try {
            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const decodedChunk = decoder.decode(value, { stream: true });
                const lines = decodedChunk.split('\n\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        setStreamingContent(prev => [...prev, data]);
                        
                        if (data.status === "Complete") {
                            setSummary(data.final_summary);
                            setReportTitle(data.report_title);
                            setReportSubtitle(data.report_subtitle);
                            setChunkSummaries(data.chunk_summaries);
                            setTranscript(data.transcript);
                            setAnalysisComplete(true);
                            setActiveResultTab("final");
                        } else if (data.status === "Transcribing") {
                            setTranscript(prev => prev + data.chunk);
                        } else if (data.type === "chunk") {
                            setChunkSummaries(prev => [...prev, data.summary]);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Error during analysis:", error);
            alert("An error occurred during analysis. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleHistoryItemClick = async (id) => {
        try {
            const response = await fetch(`/get_analysis/${id}`);
            if (!response.ok) {
                throw new Error('Failed to fetch analysis');
            }
            const data = await response.json();
            setTranscript(data.transcript);
            setSummary(data.final_summary);
            setChunkSummaries(data.chunk_summaries);
            setReportTitle(data.report_title);
            setReportSubtitle(data.report_subtitle);
            setAnalysisComplete(true);
            setActiveResultTab("final");
        } catch (error) {
            console.error("Error fetching historical analysis:", error);
            alert("Failed to load analysis. Please try again.");
        }
    };

    const startNewChat = () => {
        setAnalysisComplete(false);
        setTranscript('');
        setYoutubeLink('');
        setSummary('');
        setChunkSummaries([]);
        setReportTitle('');
        setReportSubtitle('');
        setInputType('text');
        setReportType('analyst');
        setActiveResultTab("transcript");
        setStreamingContent([]);
    };

    return (
        <div className="flex">
            <Sidebar onHistoryItemClick={handleHistoryItemClick} />
            <div className="main-content">
                <header className="mb-8 flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-blue-400 mb-2">Insights Machine Pro</h1>
                        <p className="text-xl text-gray-400">Transform your content into actionable insights</p>
                    </div>
                    <button onClick={startNewChat} className="btn btn-primary">
                        Start New Analysis
                    </button>
                </header>

                {!analysisComplete ? (
                    <>
                        <form onSubmit={handleSubmit} className="space-y-6 bg-gray-800 p-6 rounded-lg shadow-lg">
                            <div>
                                <h2 className="text-xl font-semibold mb-2">1. Choose Input Type</h2>
                                <div className="flex space-x-4">
                                    <label className="inline-flex items-center">
                                        <input type="radio" className="form-radio text-blue-500" name="input_type" value="text" checked={inputType === 'text'} onChange={() => setInputType('text')} />
                                        <span className="ml-2">Text Input</span>
                                    </label>
                                    <label className="inline-flex items-center">
                                        <input type="radio" className="form-radio text-blue-500" name="input_type" value="youtube" checked={inputType === 'youtube'} onChange={() => setInputType('youtube')} />
                                        <span className="ml-2">YouTube Link</span>
                                    </label>
                                </div>
                            </div>
                            
                            {inputType === 'text' ? (
                                <textarea
                                    name="transcript"
                                    placeholder="Enter your text here..."
                                    value={transcript}
                                    onChange={(e) => setTranscript(e.target.value)}
                                    className="w-full p-3 input-field rounded-md min-h-[200px]"
                                    required
                                />
                            ) : (
                                <input
                                    type="url"
                                    name="youtube_link"
                                    placeholder="Enter YouTube video URL"
                                    value={youtubeLink}
                                    onChange={(e) => setYoutubeLink(e.target.value)}
                                    className="w-full p-3 input-field rounded-md"
                                    required
                                />
                            )}
                            
                            <div>
                                <h2 className="text-xl font-semibold mb-2">2. Select Report Type</h2>
                                <div className="flex space-x-4">
                                    <label className="inline-flex items-center">
                                        <input type="radio" className="form-radio text-blue-500" name="report_type" value="analyst" checked={reportType === 'analyst'} onChange={() => setReportType('analyst')} />
                                        <span className="ml-2">Professional Analyst Report</span>
                                    </label>
                                    <label className="inline-flex items-center">
                                        <input type="radio" className="form-radio text-blue-500" name="report_type" value="medium" checked={reportType === 'medium'} onChange={() => setReportType('medium')} />
                                        <span className="ml-2">Engaging Medium Blog Post</span>
                                    </label>
                                </div>
                            </div>

                            <button type="submit" className="btn btn-primary w-full" disabled={loading}>
                                {loading ? "Analyzing..." : "Generate Insights"}
                            </button>
                        </form>
                        {loading && (
                            <div className="streaming-content mt-4">
                                {streamingContent.map((content, index) => (
                                    <p key={index}>
                                        {content.status}: {content.summary || content.chunk || ''}
                                    </p>
                                ))}
                            </div>
                        )}
                    </>
                ) : (
                    <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
                        <div className="mb-8 flex space-x-4">
                            {["transcript", "chunk", "final"].map((tab) => (
                                <button 
                                    key={tab}
                                    onClick={() => setActiveResultTab(tab)} 
                                    className={`tab-button ${activeResultTab === tab ? "active" : ""}`}
                                >
                                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                                </button>
                            ))}
                        </div>
                        <div className="mt-4">
                            {activeResultTab === "transcript" && (
                                <div>
                                    <h3 className="text-2xl font-semibold mb-4 text-blue-300">Original Transcript</h3>
                                    <p className="whitespace-pre-wrap">{transcript}</p>
                                </div>
                            )}
                            {activeResultTab === "chunk" && (
                                <div>
                                    <h3 className="text-2xl font-semibold mb-4 text-blue-300">Chunk Summaries</h3>
                                    {chunkSummaries.map((chunk, index) => (
                                        <div key={index} className="mb-4 bg-gray-700 p-4 rounded">
                                            <h4 className="text-xl font-semibold mb-2 text-blue-200">Chunk {index + 1}</h4>
                                            <p>{chunk}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {activeResultTab === "final" && (
                                <div>
                                    <h2 className="summary-title">{reportTitle}</h2>
                                    <p className="summary-subtitle">{reportSubtitle}</p>
                                    <div dangerouslySetInnerHTML={{ __html: summary }} />
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

function App() {
    return <TranscriptSummarizer />;
}

window.App = App;
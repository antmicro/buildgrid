.. _architecture-overview:

Remote execution overview
=========================

Remote execution aims to speed up a build process and to rely on two separate
but related concepts that are remote caching and remote execution itself. Remote
caching allows users to share build outputs while remote execution allows the running
of operations on a remote cluster of machines which may be more powerful than what
the user has access to locally.

The `Remote Execution API`_ (REAPI) describes a `gRPC`_ + `protocol-buffers`_
interface that has three main services for remote caching and execution:

- A ``ContentAddressableStorage`` (CAS) service: a remote storage end-point
  where content is addressed by digests, a digest being a pair of the hash and
  size of the data stored or retrieved.
- An ``ActionCache`` (AC) service: a mapping between build actions already
  performed and their corresponding resulting artifact.
- An ``Execution`` service: the main end-point allowing one to request build
  job to be perform against the build farm.

The `Remote Worker API`_ (RWAPI) describes another `gRPC`_ + `protocol-buffers`_
interface that allows a central ``BotsService`` to manage a farm of pluggable workers.

BuildGrid is combining these two interfaces in order to provide a complete
remote caching and execution service. The high level architecture can be
represented like this:

.. graphviz::
   :align: center

    digraph remote_execution_overview {
	node [shape = record,
	      width=2,
	      height=1];

	ranksep = 2
	compound=true
	edge[arrowtail="vee"];
	edge[arrowhead="vee"];

	client [label = "Client",
	color="#0342af",
	fillcolor="#37c1e8",
	style=filled,
	shape=box]

	database [label = "Database",
	color="#8a2be2",
	fillcolor="#9370db",
	style=filled,
	shape=box]

	subgraph cluster_controller{
	    label = "Controller";
	    labeljust = "c";
	    fillcolor="#42edae";
	    style=filled;
	    controller [label = "{ExecutionService|BotsInterface\n}",
			fillcolor="#17e86a",
			style=filled];

	}

	subgraph cluster_worker0 {
	    label = "Worker 1";
	    labeljust = "c";
	    color="#8e7747";
	    fillcolor="#ffda8e";
	    style=filled;
	    bot0 [label = "{Bot|Host-tools}"
		  fillcolor="#ffb214",
		  style=filled];
	}

	subgraph cluster_worker1 {
	    label = "Worker 2";
	    labeljust = "c";
	    color="#8e7747";
	    fillcolor="#ffda8e";
	    style=filled;
	    bot1 [label = "{Bot|BuildBox}",
		  fillcolor="#ffb214",
		  style=filled];
	}

	client -> controller [
	    dir = "both",
	    headlabel = "REAPI",
	    labelangle = 20.0,
	    labeldistance = 9,
	    labelfontsize = 15.0,
	    lhead=cluster_controller];

	 database -> controller [
	    dir = "both",
	    headlabel = "SQL",
	    labelangle = 20.0,
	    labeldistance = 9,
	    labelfontsize = 15.0,
	    lhead=cluster_controller];

	controller -> bot0 [
	    dir = "both",
	    labelangle= 340.0,
		labeldistance = 7.5,
		labelfontsize = 15.0,
	    taillabel = "RWAPI     ",
	    lhead=cluster_worker0,
	    ltail=cluster_controller];

	controller -> bot1 [
	    dir = "both",
	    labelangle= 20.0,
	    labeldistance = 7.5,
	    labelfontsize = 15.0,
		taillabel = "     RWAPI",
	    lhead=cluster_worker1,
	    ltail=cluster_controller];

    }

BuildGrid can be split up into separate endpoints. It is possible to have
a separate ``ActionCache`` and ``CAS`` from the ``Controller``. The
following diagram shows a typical setup.

.. graphviz::
   :align: center

    digraph remote_execution_overview {

	node [shape=record,
	      width=2,
	      height=1];

	compound=true
	graph [nodesep=1,
	       ranksep=2]

	edge[arrowtail="vee"];
	edge[arrowhead="vee"];

	client [label="Client",
		color="#0342af",
		fillcolor="#37c1e8",
		style=filled,
		shape=box]
	
        database [label = "Database",
	          color="#8a2be2",
	          fillcolor="#9370db",
	          style=filled,
	          shape=box]

	cas [label="CAS",
	     color="#840202",
	     fillcolor="#c1034c",
	     style=filled,
	     shape=box]

	subgraph cluster_controller{
	    label="Controller";
	    labeljust="c";
	    fillcolor="#42edae";
	    style=filled;
	    controller [label="{ExecutionService|BotsInterface\n}",
			fillcolor="#17e86a",
			style=filled];

	}

	actioncache [label="ActionCache",
		     color="#133f42",
		     fillcolor="#219399",
		     style=filled,
		     shape=box]

	subgraph cluster_worker0 {
	    label="Worker";
	    labeljust="c";
	    color="#8e7747";
	    fillcolor="#ffda8e";
	    style=filled;
	    bot0 [label="{Bot}"
		  fillcolor="#ffb214",
		  style=filled];
	}

	client -> controller [
	    dir="both"];

	database -> controller [
	    dir="both"];

	client -> cas [
	    dir="both",
	    lhead=cluster_controller];

	controller -> bot0 [
	    dir="both",
	    lhead=cluster_worker0];
	    //ltail=cluster_controller];

	cas -> bot0 [
	    dir="both",
	    lhead=cluster_worker0];

	actioncache -> controller [
	    dir="both"];

	client -> actioncache [
	    dir="both",
	    constraint=false,
    ];


    }

The flow of BuildGrid requests
==============================

BuildGrid uses various threads to achieve different tasks.
The following diagram is an overview of the interactions between components of BuildGrid
in response to a GRPC Request.

The Light Green color is used to signify distinct threads, and entities outside of
the green boxes are shared among all threads.

.. graphviz::
   :align: center

	digraph buildgrid_overview {
		node [shape=record,
			width=2,
			height=1];

		fontsize=16;
		compound=true;
		graph [nodesep=0.1,
			   ranksep=0]

		edge [arrowtail="vee",
			arrowhead="vee",
			fontsize=16,
			fontcolor="#02075D",
			color="#02075D",];

		splines=polyline;
        rankdir=LR;

		subgraph cluster_clients{
			label="GRPC Clients\n(REAPI/RWAPI)";
			labeljust="c";
			fillcolor="#ffccdd";
			style=filled;
			clients [label="Remote Execution Clients|Bots|CAS Clients\n",
				fillcolor="#ff998e",
				style=filled]
		}

		subgraph cluster_bgd {
			label="BuildGrid Process";
			labeljust="c";
			fillcolor="#ffda8e";
			style=filled;

			subgraph cluster_bgd_services {
				label="BuildGrid Services";
				labeljust="c";
				fillcolor="#ffb214";
				fontsize=14;
				bgd_services [
					label="Execution|Bots|CAS\n",
					fillcolor="#ffb214",
					style=filled]
			}

			subgraph cluster_data {
				label="Persistent Data";
				labeljust="c";
				fillcolor="#9370db";
				data [label="CAS Backend";shape=cylinder;]
				data_store [label="DataStore";shape=cylinder;]
			}

			jobwatcher [
				label="Job Watcher Thread",
				labeljust="c",
				fillcolor="#42edae",
				fontsize=14,
				style=filled,
			]

			subgraph cluster_mainthread {
				label="Main Thread";
				fillcolor="#42edae";
				fontsize=14;
				subgraph cluster_asyncioloop {
					label="asyncio loop";
					labeljust="c";
					fillcolor="#00A572";
					style=filled;
					asyncio_loop [label="Metrics & Logging|BotSession Reaper\n",
						fillcolor="#29AB87",
						style=filled];
				}
			}

			subgraph cluster_grpc {
				label="GRPC Thread";
				fillcolor="#42edae";
				fontsize=14;
				subgraph cluster_grpcserver{
					label="GRPC Server";
					labeljust="c";
					fillcolor="#37c1e8";
					style=filled;
					grpc_server [label="unary_unary|unary_stream\n",
						fillcolor="#37c1cc",
						style=filled];
				}

				grpccb [
					label="Pluggable\nTermination Callback\n(per request type)",
					fillcolor="#37c1cc",
					style=filled,
				]
			}

			subgraph cluster_grpcservicer {
				label="GRPC Servicer\n(Running within ThreadPool)\n`gRPC_Executor_n`";
				labeljust="c";
				fillcolor="#42edae";
				style=filled;
				fontsize=14;
				grpc_servicer [label="def Execute:\l|def WaitExecute:\l|def ...:\l",
					fillcolor="#17e86a",
					style=filled];
			}

			grpc_server -> grpc_servicer [
				dir="forward",
				label="2. ThreadPool.submit()",
				ltail=cluster_grpcserver,
				lhead=cluster_grpcservicer
			]

			grpc_servicer -> grpc_server [
				dir="forward",
				label="3. Prepares response",
				lhead=cluster_grpcserver,
				ltail=cluster_grpcservicer
			]

			grpc_server -> grpccb [
				dir="forward",
				label="5. Calls Termination Callback\n(optional)",
				lhead=cluster_grpcserver,
			]

		}

		clients -> grpc_server [
			dir="forward",
			label="1.\ngrpc:Execute\lgrpc:WaitExecute\lgrpc:...\l",
			lhead=cluster_grpcserver,
			ltail = cluster_clients,
		];

		grpc_server -> clients[
			dir="forward",
			label="4. Sends Response",
			ltail=cluster_grpcserver,
			lhead = cluster_clients,
		];


		# Invisible edges to improve the layout
		bgd_services -> data [style=invis];
		asyncio_loop -> data_store [style=invis];
		data -> jobwatcher [style=invis];
		
		}





.. _Remote Execution API: https://github.com/bazelbuild/remote-apis/blob/master/build/bazel/remote/execution/v2
.. _gRPC: https://grpc.io
.. _protocol-buffers: https://developers.google.com/protocol-buffers
.. _Remote Worker API: https://github.com/googleapis/googleapis/tree/master/google/devtools/remoteworkers/v1test2

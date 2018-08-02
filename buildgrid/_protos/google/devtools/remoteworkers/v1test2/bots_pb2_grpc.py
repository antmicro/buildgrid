# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from buildgrid._protos.google.devtools.remoteworkers.v1test2 import bots_pb2 as google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2


class BotsStub(object):
  """Design doc: https://goo.gl/oojM5H

  Loosely speaking, the Bots interface monitors a collection of workers (think
  of them as "computers" for a moment). This collection is known as a "farm,"
  and its purpose is to perform work on behalf of a client.

  Each worker runs a small program known as a "bot" that allows it to be
  controlled by the server. This interface contains only methods that are
  called by the bots themselves; admin functionality is out of scope for this
  interface.

  More precisely, we use the term "worker" to refer to the physical "thing"
  running the bot. We use the term "worker," and not "machine" or "computer,"
  since a worker may consist of more than one machine - e.g., a computer with
  multiple attached devices, or even a cluster of computers, with only one of
  them running the bot. Conversely, a single machine may host several bots, in
  which case each bot has a "worker" corresponding to the slice of the machine
  being managed by that bot.

  The main resource in the Bots interface is not, surprisingly, a Bot - it is a
  BotSession, which represents a period of time in which a bot is in continuous
  contact with the server (see the BotSession message for more information).
  The parent of a bot session can be thought of as an instance of a farm. That
  is, one endpoint may be able to manage many farms for many users. For
  example, for a farm managed through GCP, the parent resource will typically
  take the form "projects/{project_id}". This is referred to below as "the farm
  resource."
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.CreateBotSession = channel.unary_unary(
        '/google.devtools.remoteworkers.v1test2.Bots/CreateBotSession',
        request_serializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.CreateBotSessionRequest.SerializeToString,
        response_deserializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.BotSession.FromString,
        )
    self.UpdateBotSession = channel.unary_unary(
        '/google.devtools.remoteworkers.v1test2.Bots/UpdateBotSession',
        request_serializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.UpdateBotSessionRequest.SerializeToString,
        response_deserializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.BotSession.FromString,
        )
    self.PostBotEventTemp = channel.unary_unary(
        '/google.devtools.remoteworkers.v1test2.Bots/PostBotEventTemp',
        request_serializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.PostBotEventTempRequest.SerializeToString,
        response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
        )


class BotsServicer(object):
  """Design doc: https://goo.gl/oojM5H

  Loosely speaking, the Bots interface monitors a collection of workers (think
  of them as "computers" for a moment). This collection is known as a "farm,"
  and its purpose is to perform work on behalf of a client.

  Each worker runs a small program known as a "bot" that allows it to be
  controlled by the server. This interface contains only methods that are
  called by the bots themselves; admin functionality is out of scope for this
  interface.

  More precisely, we use the term "worker" to refer to the physical "thing"
  running the bot. We use the term "worker," and not "machine" or "computer,"
  since a worker may consist of more than one machine - e.g., a computer with
  multiple attached devices, or even a cluster of computers, with only one of
  them running the bot. Conversely, a single machine may host several bots, in
  which case each bot has a "worker" corresponding to the slice of the machine
  being managed by that bot.

  The main resource in the Bots interface is not, surprisingly, a Bot - it is a
  BotSession, which represents a period of time in which a bot is in continuous
  contact with the server (see the BotSession message for more information).
  The parent of a bot session can be thought of as an instance of a farm. That
  is, one endpoint may be able to manage many farms for many users. For
  example, for a farm managed through GCP, the parent resource will typically
  take the form "projects/{project_id}". This is referred to below as "the farm
  resource."
  """

  def CreateBotSession(self, request, context):
    """CreateBotSession is called when the bot first joins the farm, and
    establishes a session ID to ensure that multiple machines do not register
    using the same name accidentally.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def UpdateBotSession(self, request, context):
    """UpdateBotSession must be called periodically by the bot (on a schedule
    determined by the server) to let the server know about its status, and to
    pick up new lease requests from the server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def PostBotEventTemp(self, request, context):
    """PostBotEventTemp may be called by the bot to indicate that some exceptional
    event has occurred. This method is subject to change or removal in future
    revisions of this API; we may simply want to replace it with StackDriver or
    some other common interface.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_BotsServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'CreateBotSession': grpc.unary_unary_rpc_method_handler(
          servicer.CreateBotSession,
          request_deserializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.CreateBotSessionRequest.FromString,
          response_serializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.BotSession.SerializeToString,
      ),
      'UpdateBotSession': grpc.unary_unary_rpc_method_handler(
          servicer.UpdateBotSession,
          request_deserializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.UpdateBotSessionRequest.FromString,
          response_serializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.BotSession.SerializeToString,
      ),
      'PostBotEventTemp': grpc.unary_unary_rpc_method_handler(
          servicer.PostBotEventTemp,
          request_deserializer=google_dot_devtools_dot_remoteworkers_dot_v1test2_dot_bots__pb2.PostBotEventTempRequest.FromString,
          response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'google.devtools.remoteworkers.v1test2.Bots', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))